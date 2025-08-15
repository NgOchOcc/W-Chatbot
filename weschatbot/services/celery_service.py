import logging

from weschatbot.models.job import Job, JobStatus
from weschatbot.services.document.index_document_service import IndexDocumentService, DocumentConverter, \
    PipelineMilvusStore
from weschatbot.utils.config import config
from weschatbot.utils.db import provide_session
from weschatbot.worker.celery_worker import celery_app
from functools import wraps

app = celery_app()


def update_job_status(func):
    @provide_session
    def update(job_id, status, session=None):
        status_entity = session.query(JobStatus).filter(JobStatus.name == status).one_or_none()
        if not status_entity:
            raise ValueError(f"Unknown status '{status}'. Please run command 'alembic upgrade head' to upgrade db.")
        job_run = session.get(Job, job_id)
        job_run.status = status_entity

    @wraps(func)
    def wrapper(job_id, *args, **kwargs):
        try:
            logging.info(f"Running {func.__name__}; job run {job_id}")
            func(*args, **kwargs)
            status = "done"
            logging.info(f"Finished {func.__name__}; job run {job_id}")
        except Exception as e:
            logging.error(e)
            status = "failed"
            logging.error(f"Failed {func.__name__}; job run {job_id}")
        update(job_id, status)

    return wrapper


@app.task
@update_job_status
def add(a, b):
    print(f"Done result: {a + b}")
    return a + b


@app.task
@update_job_status
def index_documents():
    converter = DocumentConverter()
    pipeline = PipelineMilvusStore(collection_name=config["core"]["milvus_collection_name"],
                                   milvus_host=config["milvus"]["host"],
                                   milvus_port=config["milvus"]["port"])
    indexer = IndexDocumentService(converter=converter, pipeline=pipeline)
    indexer.index()
