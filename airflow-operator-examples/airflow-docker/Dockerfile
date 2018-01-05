FROM puckel/docker-airflow:latest

USER root
RUN set -ex \
    && rm /usr/local/airflow/airflow.cfg \
    && rm -Rf /usr/local/lib/python3.6/site-packages/airflow/example_dags/*

USER airflow
RUN for var in $(env | grep AIRFLOW_ | cut -d '=' -f 1); do unset $var; done
RUN LOAD_EX=n airflow initdb
RUN mkdir -p /usr/local/airflow/airflow/dags

USER root
RUN set -ex \
    && apt-get update -yqq \
    && apt-get install -yqq --no-install-recommends \
        libmysqlclient-dev \
        freetds-dev \
    && pip install apache-airflow[all]==1.8.2 \
    && pip install google-api-python-client \
    && pip install pandas-gbq \
    && pip uninstall --yes snakebite \
    && apt-get purge --auto-remove -yqq $buildDeps \
    && apt-get clean \
    && rm -rf \
        /var/lib/apt/lists/* \
        /tmp/* \
        /var/tmp/* \
        /usr/share/man \
        /usr/share/doc \
        /usr/share/doc-base

COPY entrypoint.sh /entrypoint.sh

USER airflow

ENTRYPOINT [ "/entrypoint.sh" ]
CMD [ "argo-airflow-dag" ] 
