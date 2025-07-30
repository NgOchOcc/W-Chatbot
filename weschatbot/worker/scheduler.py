import json
import logging

from weschatbot.models.job import Job, JobStatus
from weschatbot.utils.common import create_object_from_class_name, get_function_by_fullname
from weschatbot.utils.db import provide_session


@provide_session
def execute_job_runs(session=None):
    jobs = session.query(Job).filter(Job.status.has(name="approved")).all()
    job_tasks = [(job.class_name, job) for job in jobs]
    for task, job in job_tasks:
        scheduled_status = session.query(JobStatus).filter("scheduled" == JobStatus.name).one_or_none()
        if scheduled_status:
            job.status = scheduled_status
        else:
            raise ValueError("Not found scheduled status. Please upgrade you db by command 'alembic upgrade head'")

        func = get_function_by_fullname(job.class_name)
        params = json.loads(job.params)
        func.delay(job.id, **params)
        logging.warning(f"Scheduled job run {job} for task {task}")


@provide_session
def schedule(session=None):
    while True:
        execute_job_runs()
