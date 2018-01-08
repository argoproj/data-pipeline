from datetime import timedelta, datetime
import json
import os

from airflow import DAG, settings
from airflow.contrib.operators.bigquery_operator import BigQueryOperator
from airflow.contrib.operators.bigquery_check_operator import BigQueryCheckOperator
from airflow.operators.python_operator import PythonOperator
from airflow.models import Connection

default_args = {
    'owner': 'airflow',
    'depends_on_past': True,
    'start_date': datetime(2017, 6, 2),
    'email': ['airflow@airflow.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
}

def add_gcp_connection(ds, **kwargs):
    """"Add a airflow connection for GCP"""
    new_conn = Connection(
        conn_id='bigquery',
        conn_type='google_cloud_platform',
    )
    scopes = [
        "https://www.googleapis.com/auth/bigquery",
    ]
    conn_extra = {
        "extra__google_cloud_platform__scope": ",".join(scopes),
        "extra__google_cloud_platform__project": os.environ['GOOGLE_CLOUD_PROJECT'],
        "extra__google_cloud_platform__key_path": os.environ['AIRFLOW_CONN_GOOGLE_CLOUD_PLATFORM']
    }
    conn_extra_json = json.dumps(conn_extra)
    new_conn.set_extra(conn_extra_json)

    session = settings.Session()
    if not (session.query(Connection).filter(Connection.conn_id == new_conn.conn_id).first()):
        session.add(new_conn)
        session.commit()
    else:
        msg = '\n\tA connection with `conn_id`={conn_id} already exists\n'
        msg = msg.format(conn_id=new_conn.conn_id)
        print(msg)

dag = DAG('bigquery_github_trends_v1', default_args=default_args, schedule_interval="@once")

# Task to add a connection
t0 = PythonOperator(
    dag=dag,
    task_id='add_gcp_connection_python',
    python_callable=add_gcp_connection,
    provide_context=True,
)

t1 = BigQueryOperator(
    task_id='bq_write_to_hackernews_github_agg',
    bigquery_conn_id='bigquery',
    use_legacy_sql=False,
    write_disposition='WRITE_TRUNCATE',
    allow_large_results=True,
    bql='''
    #standardSQL
    SELECT
    a.date as date,
    a.url as github_url,
    b.repo as github_repo,
    a.score as hn_score,
    a.story_id as hn_story_id,
    b.stars_last_28_days as stars_last_28_days,
    b.stars_last_7_days as stars_last_7_days,
    b.stars_last_1_day as stars_last_1_day,
    b.forks_last_28_days as forks_last_28_days,
    b.forks_last_7_days as forks_last_7_days,
    b.forks_last_1_day as forks_last_1_day
    FROM
    (SELECT
      *
    FROM
      `github_trends.hackernews_agg`
      WHERE _PARTITIONTIME BETWEEN TIMESTAMP("{{ yesterday_ds }}") AND TIMESTAMP("{{ yesterday_ds }}")
      )as a
    LEFT JOIN
      (
      SELECT
      repo,
      CONCAT('https://github.com/', repo) as url,
      stars_last_28_days,
      stars_last_7_days,
      stars_last_1_day,
      forks_last_28_days,
      forks_last_7_days,
      forks_last_1_day
      FROM
      `github_trends.github_agg`
      WHERE _PARTITIONTIME BETWEEN TIMESTAMP("{{ yesterday_ds }}") AND TIMESTAMP("{{ yesterday_ds }}")
      ) as b
    ON a.url = b.url
    ''',
    destination_dataset_table='github_trends.hackernews_github_agg${{ yesterday_ds_nodash }}',
    dag=dag)

t1.set_upstream(t0)
