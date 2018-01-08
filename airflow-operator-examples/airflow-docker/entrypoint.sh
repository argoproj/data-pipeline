#!/bin/bash

AIRFLOW_HOME="/usr/local/airflow"

if [ -e "/requirements.txt" ]; then
    $(which pip) install --user -r /requirements.txt
fi

if [ "$1" != "argo-airflow-dag" ]
then
  exec "$@"
  exit $?
fi

if [ -z ${DAG_NAME+x} ]
then
  echo "DAG_NAME is not set. Cannot run without DAG_NAME environment variable"
  exit 1
fi

echo "sd: ${START_DATE}"

DATE_ARGS=""
if [[ -z "${START_DATE}" ]]
then
  START_DATE="$(date +%Y%m%d)"
fi
DATE_ARGS="${DATE_ARGS} -s ${START_DATE}"

airflow backfill ${DATE_ARGS} ${DAG_NAME}
RET=$?
if [ ${RET} -ne 0 ]
then
  if [ -d ${AIRFLOW_HOME}/airflow/logs ]
  then
    cd ${AIRFLOW_HOME}/airflow/logs
    for dag_dir in $(find . -maxdepth 1 -mindepth 1 -type d)
    do
      cd "${dag_dir}"
      for task_dir in $(find . -maxdepth 1 -mindepth 1 -type d)
      do
        echo ""
        echo "----------------------------------------------------"
        echo "BEGIN - DAG: ${dag_dir} - TASK: ${task_dir}"
        echo "----------------------------------------------------"
        cd "${task_dir}"
        for log in $(find . -maxdepth 1 -mindepth 1 -type f)
        do
          echo ""
          echo "====================================================="
          echo "BEGIN - DAG: ${dag_dir} - TASK: ${task_dir} - LOG: ${log}"
          echo "====================================================="
          cat "${log}"
          echo "====================================================="
          echo "END - DAG: ${dag_dir} - TASK: ${task_dir} - LOG: ${log}"
          echo "====================================================="
	  echo ""          
        done
        cd ..
        echo "----------------------------------------------------"
        echo "END - DAG: ${dag_dir} - TASK: ${task_dir}"
        echo "----------------------------------------------------"
      done
      cd ..
    done
  fi
fi
exit ${RET}
