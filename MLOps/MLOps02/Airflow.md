# MLOps Node4. AirFlow
2026.04.16 ~ 04.17 

## Airflow 구성 1
### 🚨"Invalid key JSON 에러 해결
- 터미널을 통해 key를 발급하여 사용
1. GCP CLI 설치
```
# 1. 파일 다운로드 (URL 주위에 < > 를 뺐습니다) 
Invoke-WebRequest -Uri "https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe" -OutFile "$env:Temp\GoogleCloudSDKInstaller.exe"
# 2. 설치 관리자 실행 
Start-Process "$env:Temp\GoogleCloudSDKInstaller.exe" -Wait
```
2. ADC 인증 처리
```
gcloud auth application-default set-quota-project [프로젝트ID]
```
3. 서비스 계정 키(JSON) 발급
```
# 서비스 계정확인하기
gcloud iam service-accounts list
````
```
# 이미있는 서비스 계정으로 키 발급받기
gcloud iam service-accounts keys create my-key.json --iam-account=[서비스계정명]@[프로젝트ID].iam.gserviceaccount.com
```
```
# 권한 한번더 확인하기
gcloud projects add-iam-policy-binding sandbox-493404 --member="serviceAccount:mlops-airflow@sandbox-493404.iam.gserviceaccount.com" --role="roles/bigquery.admin"
```
4. Airflow 자원정리
```
docker compose down --volumes --rmi all
```
5. Airflow 실행
```
docker compose up -d
```
### 작동화면
<img width="997" height="458" alt="image" src="https://github.com/user-attachments/assets/210ff09e-e7dd-4b7a-b535-7de05f7a67a2" />
### Log 기록
```
644900c573cd
*** Found local files:
***   * /opt/airflow/logs/dag_id=bigquery_airflow_example/run_id=scheduled__2026-04-16T00:00:00+00:00/task_id=bq_query_example/attempt=2.log
[2026-04-17, 07:41:44 UTC] {taskinstance.py:1979} INFO - Dependencies all met for dep_context=non-requeueable deps ti=<TaskInstance: bigquery_airflow_example.bq_query_example scheduled__2026-04-16T00:00:00+00:00 [queued]>
[2026-04-17, 07:41:44 UTC] {taskinstance.py:1979} INFO - Dependencies all met for dep_context=requeueable deps ti=<TaskInstance: bigquery_airflow_example.bq_query_example scheduled__2026-04-16T00:00:00+00:00 [queued]>
[2026-04-17, 07:41:44 UTC] {taskinstance.py:2193} INFO - Starting attempt 2 of 2
[2026-04-17, 07:41:44 UTC] {taskinstance.py:2217} INFO - Executing <Task(BigQueryExecuteQueryOperator): bq_query_example> on 2026-04-16 00:00:00+00:00
[2026-04-17, 07:41:44 UTC] {standard_task_runner.py:60} INFO - Started process 256 to run task
[2026-04-17, 07:41:44 UTC] {standard_task_runner.py:87} INFO - Running: ['***', 'tasks', 'run', 'bigquery_***_example', 'bq_query_example', 'scheduled__2026-04-16T00:00:00+00:00', '--job-id', '4', '--raw', '--subdir', 'DAGS_FOLDER/bigquery_***_example.py', '--cfg-path', '/tmp/tmpl3m3tfb9']
[2026-04-17, 07:41:44 UTC] {standard_task_runner.py:88} INFO - Job 4: Subtask bq_query_example
[2026-04-17, 07:41:45 UTC] {task_command.py:423} INFO - Running <TaskInstance: bigquery_airflow_example.bq_query_example scheduled__2026-04-16T00:00:00+00:00 [running]> on host c7bf9689cce4
[2026-04-17, 07:41:45 UTC] {taskinstance.py:2513} INFO - Exporting env vars: AIRFLOW_CTX_DAG_OWNER='***' AIRFLOW_CTX_DAG_ID='bigquery_***_example' AIRFLOW_CTX_TASK_ID='bq_query_example' AIRFLOW_CTX_EXECUTION_DATE='2026-04-16T00:00:00+00:00' AIRFLOW_CTX_TRY_NUMBER='2' AIRFLOW_CTX_DAG_RUN_ID='scheduled__2026-04-16T00:00:00+00:00'
[2026-04-17, 07:41:45 UTC] {bigquery.py:1246} INFO - Executing: SELECT * FROM `bigquery-public-data.samples.github_nested`
[2026-04-17, 07:41:45 UTC] {taskinstance.py:2731} ERROR - Task failed with exception
Traceback (most recent call last):
  File "/home/airflow/.local/lib/python3.8/site-packages/airflow/models/taskinstance.py", line 444, in _execute_task
    result = _execute_callable(context=context, **execute_callable_kwargs)
  File "/home/airflow/.local/lib/python3.8/site-packages/airflow/models/taskinstance.py", line 414, in _execute_callable
    return execute_callable(context=context, **execute_callable_kwargs)
  File "/home/airflow/.local/lib/python3.8/site-packages/airflow/providers/google/cloud/operators/bigquery.py", line 1247, in execute
    self.hook = BigQueryHook(
  File "/home/airflow/.local/lib/python3.8/site-packages/airflow/providers/google/cloud/hooks/bigquery.py", line 119, in __init__
    super().__init__(
  File "/home/airflow/.local/lib/python3.8/site-packages/airflow/providers/google/common/hooks/base_google.py", line 251, in __init__
    self.extras: dict = self.get_connection(self.gcp_conn_id).extra_dejson
  File "/home/airflow/.local/lib/python3.8/site-packages/airflow/hooks/base.py", line 82, in get_connection
    conn = Connection.get_connection_from_secrets(conn_id)
  File "/home/airflow/.local/lib/python3.8/site-packages/airflow/models/connection.py", line 514, in get_connection_from_secrets
    raise AirflowNotFoundException(f"The conn_id `{conn_id}` isn't defined")
airflow.exceptions.AirflowNotFoundException: The conn_id `google_cloud_default` isn't defined
[2026-04-17, 07:41:45 UTC] {taskinstance.py:1149} INFO - Marking task as FAILED. dag_id=bigquery_***_example, task_id=bq_query_example, execution_date=20260416T000000, start_date=20260417T074144, end_date=20260417T074145
[2026-04-17, 07:41:45 UTC] {standard_task_runner.py:107} ERROR - Failed to execute job 4 for task bq_query_example (The conn_id `google_cloud_default` isn't defined; 256)
[2026-04-17, 07:41:45 UTC] {local_task_job_runner.py:234} INFO - Task exited with return code 1
[2026-04-17, 07:41:46 UTC] {taskinstance.py:3312} INFO - 0 downstream tasks scheduled from follow-on schedule check
[2026-04-17, 09:38:50 UTC] {taskinstance.py:1979} INFO - Dependencies all met for dep_context=non-requeueable deps ti=<TaskInstance: bigquery_airflow_example.bq_query_example scheduled__2026-04-16T00:00:00+00:00 [queued]>
[2026-04-17, 09:38:50 UTC] {taskinstance.py:1979} INFO - Dependencies all met for dep_context=requeueable deps ti=<TaskInstance: bigquery_airflow_example.bq_query_example scheduled__2026-04-16T00:00:00+00:00 [queued]>
[2026-04-17, 09:38:50 UTC] {taskinstance.py:2193} INFO - Starting attempt 2 of 2
[2026-04-17, 09:38:50 UTC] {taskinstance.py:2217} INFO - Executing <Task(BigQueryExecuteQueryOperator): bq_query_example> on 2026-04-16 00:00:00+00:00
[2026-04-17, 09:38:50 UTC] {standard_task_runner.py:60} INFO - Started process 250 to run task
[2026-04-17, 09:38:50 UTC] {standard_task_runner.py:87} INFO - Running: ['***', 'tasks', 'run', 'bigquery_***_example', 'bq_query_example', 'scheduled__2026-04-16T00:00:00+00:00', '--job-id', '4', '--raw', '--subdir', 'DAGS_FOLDER/bigquery_***_example.py', '--cfg-path', '/tmp/tmppv9b1hzi']
[2026-04-17, 09:38:50 UTC] {standard_task_runner.py:88} INFO - Job 4: Subtask bq_query_example
[2026-04-17, 09:38:50 UTC] {task_command.py:423} INFO - Running <TaskInstance: bigquery_airflow_example.bq_query_example scheduled__2026-04-16T00:00:00+00:00 [running]> on host 644900c573cd
[2026-04-17, 09:38:50 UTC] {taskinstance.py:2513} INFO - Exporting env vars: AIRFLOW_CTX_DAG_OWNER='***' AIRFLOW_CTX_DAG_ID='bigquery_***_example' AIRFLOW_CTX_TASK_ID='bq_query_example' AIRFLOW_CTX_EXECUTION_DATE='2026-04-16T00:00:00+00:00' AIRFLOW_CTX_TRY_NUMBER='2' AIRFLOW_CTX_DAG_RUN_ID='scheduled__2026-04-16T00:00:00+00:00'
[2026-04-17, 09:38:50 UTC] {bigquery.py:1246} INFO - Executing: SELECT * FROM `bigquery-public-data.samples.github_nested`
[2026-04-17, 09:38:50 UTC] {connection.py:269} WARNING - Connection schemes (type: google_cloud_platform) shall not contain '_' according to RFC3986.
[2026-04-17, 09:38:50 UTC] {base.py:83} INFO - Using connection ID 'google_cloud_default' for task execution.
[2026-04-17, 09:38:50 UTC] {warnings.py:109} WARNING - /home/***/.local/lib/python3.8/site-packages/***/providers/google/cloud/operators/bigquery.py:1254: AirflowProviderDeprecationWarning: Call to deprecated method run_query. (Please use `***.providers.google.cloud.hooks.bigquery.BigQueryHook.insert_job`)
  self.job_id = self.hook.run_query(
[2026-04-17, 09:38:50 UTC] {bigquery.py:1613} INFO - Inserting job ***_1776418730534996_74851c736774c59bb5b34fb9d7ee3746
[2026-04-17, 09:39:04 UTC] {taskinstance.py:1149} INFO - Marking task as SUCCESS. dag_id=bigquery_***_example, task_id=bq_query_example, execution_date=20260416T000000, start_date=20260417T093850, end_date=20260417T093904
[2026-04-17, 09:39:04 UTC] {local_task_job_runner.py:234} INFO - Task exited with return code 0
[2026-04-17, 09:39:04 UTC] {taskinstance.py:3312} INFO - 0 downstream tasks scheduled from follow-on schedule check
```

