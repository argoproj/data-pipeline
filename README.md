# Argo workflows for data pipelines in Kubernetes native way using Apache-Airflow operators and hooks

## Concept:

There are not many open source options to do data pipelines native to modern container-orchestration system like Kubernetes. Argo allows for Kubernetes native workflows. The idea is to use the existing variety of hooks and operators available in Apache-Airflow and use them to run a data pipeline native to Kubernetes (using Kubernetes native primitives and Argo for workflow management). This allows us to define data-pipelines which are not limited to using only Apache-Airflow operators and we can using existing container images to do data operations which are either not supported in Apache Airflow or are not converted to python in some way. Argo workflows also have the advantage of being able to combine DAG's with non-DAG steps based operations in a single workflow and can launch arbitrary container images to do the operation. Argo workflow DAGs will also allow users to execute arbitrary set of tasks for a given dag with just parameters (and it would execute their dependant tasks as well)

## Architecture:

1. Break each individual task (instantiated operator) in Apache Airflow into separate files (python code used in writing Apache Airflow Dags) and define individual dags for each task.
2. As part of defining the task, we also define the connections needed for the task. These connections can usually be defined with a single environment variable in Apache Airflow, however for some connections like for google cloud, you need a separate operator (in Apache Airflow 1.8.2). See [individual airflow tasks](airflow-operator-examples/bigquery-example/tasks)
3. Use a Apache-Airflow image containing all the operators (based on v1.8.2) but running with sqllite and sequential executor to execute the tasks as individual steps/dag entries in Argo workflow
4. Use backfill in Apache-Airflow to run the individual tasks to completion in a given step
5. Using Kubernetes native [CronJob](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/) to do scheduling of workflows

## Example:

Assumptions:

1. You have a [Kubernetes 1.8](https://kubernetes.io/)  cluster already running.
2. You have a [Google Cloud](https://cloud.google.com/) account with access to BigQuery.
3. You have atleast the v1alpha3 release of [Argo](https://github.com/argoproj/argo/blob/master/demo.md)  installed and running in your Kubernetes cluster.
4. You have [kubectl v1.8.x](https://kubernetes.io/docs/tasks/tools/install-kubectl/) and [argo cli](https://github.com/argoproj/argo/blob/master/demo.md) installed on your computer
5. You have [configured your kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/) to point to your Kubernetes cluster

We use the example from Google using BigQuery related operators and Google Cloud connections to do [hacker news and github trend](https://cloud.google.com/blog/big-data/2017/07/how-to-aggregate-data-for-bigquery-using-apache-airflow)

This example uses workflows for two things:

1. To create BigQuery dataset and Tables. Then do Backfill for older dates for github daily table. You can see this in the [init Yaml](airflow-operator-examples/bigquery-example/workflows/bigquery_step_init_workflow.yaml)
2. To run the main workflow which is taken from the Google Example which you can see in the [workflow Yaml](airflow-operator-examples/bigquery-example/workflows/bigquery_step_workflow.yaml)

### How to Run the Example:

1. Get access to BigQuery:
   1. Create a Service Account in Google Cloud with BigQuery Admin Role using the IAM & admin settings in the console
   2. Download the Key.json file to your computer

2. Create Secret in Kubernetes based on the Key.json file:
   1. Create Kubernetes secret with the following command
      ```shell
      mv Key.json gcp-bigquery.json
      kubectl create secret bigquery-sa-secret --from-file=gcp-bigquery.json
      ```
      This will create a new secret called bigquery-sa-secret with key gcp-bigquery.json and the content of the gcp-bigquery.json as data in your cluster

3. Check out example repository:
   ```shell
   git clone https://github.com/argoproj/data-pipeline
   ```

4. Submit the initialization workflow:
   ```shell
   argo submit data-pipeline/airflow-operator-examples/bigquery-example/workflows/bigquery_step_init_workflow.yaml -p gcp-project="<Name of your google cloud project>"
   ```
   This will create bigquery dataset called *github_trends* and four tables *github_daily_metrics*, *github_agg*, *hackernews_agg* and *hackernews_github_agg*. It will also fill in the last 40 days of data for the table for the *github_daily_metrics* table so you don't have to keep getting that data from the public set. See the [Google example](https://cloud.google.com/blog/big-data/2017/07/how-to-aggregate-data-for-bigquery-using-apache-airflow).

5. At this point you are ready to run the full data workflow. You have two options:
   1. Run the CronJob and wait for a day to see the data fill out the final data in *hackernews_github_agg* by running the following:
      ```shell
      kubectl apply -f data-pipeline/airflow-operator-examples/bigquery-example/cronjobs/bigquery_hn_github_trends_cron.yaml
      ```

     If you do the above you need to modify the bigquery_hn_github_trends_cron.yaml to add -p gcp-project="<Name of your google cloud project>" to end of line in file **data-pipeline/airflow-operator-examples/bigquery-example/cronjobs/bigquery_hn_github_trends_cron.yaml**

      CHANGE:
      ```yaml
	apiVersion: batch/v1beta1
	kind: CronJob
	metadata:
	  name: bigquery-hn-github-trend-cron
	spec:
	  schedule: "30 23 * * *"
	  jobTemplate:
	    spec:
	      backoffLimit: 2
	      template:
		spec:
		  containers:
		  - name: submit-workflow
		    image: docker.io/argoproj/kubectl:sh-v1.8.3
		    command: ["/bin/sh", "-c"]
		    args: ["wget -O /tmp/bigquery_step_workflow.yaml https://raw.githubusercontent.com/argoproj/data-pipeline/master/airflow-operator-examples/bigquery-example/workflows/bigquery_step_workflow.yaml; kubectl create -f /tmp/bigquery_step_workflow.yaml"]
		    imagePullPolicy: Always
	restartPolicy: Never
      ```

      TO

      ```yaml
	apiVersion: batch/v1beta1
	kind: CronJob
	metadata:
	  name: bigquery-hn-github-trend-cron
	spec:
	  schedule: "30 23 * * *"
	  jobTemplate:
	    spec:
	      backoffLimit: 2
	      template:
		spec:
		  containers:
		  - name: submit-workflow
		    image: docker.io/argoproj/kubectl:sh-v1.8.3
		    command: ["/bin/sh", "-c"]
		    args: ["wget -O /tmp/bigquery_step_workflow.yaml https://raw.githubusercontent.com/argoproj/data-pipeline/master/airflow-operator-examples/bigquery-example/workflows/bigquery_step_workflow.yaml; kubectl create -f /tmp/bigquery_step_workflow.yaml -p gcp-project='<Name of your google cloud project>'"]
		    imagePullPolicy: Always
	restartPolicy: Never
      ```
     
   2. Run the workflow manually to fill out for various dates:
      ```shell
      argo submit data-pipeline/airflow-operator-examples/bigquery-example/workflows/bigquery_step_workflow.yaml -p gcp-project="<Name of your google cloud project>" -p run-date="<Yesterday's date in form YYYYMMDD>"
      ```

      The reason to use yesterday's date is that sometimes the hackernews public data set is not updated for the previous day until much later the next day. At this point you should have the *hackernews_github_agg* table filled with the data for the day the workflow ran for.

6. You can plot the table in datastudio in google cloud apps by copying from [my example](https://datastudio.google.com/open/1gCJX4-ZJKOAjq9SJEhXuNgMdMgPGcr0s) and changing the data source you point to your own tables.
