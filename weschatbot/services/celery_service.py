import asyncio
import logging
import subprocess
from functools import wraps

from weschatbot.models.job import Job, JobStatus
from weschatbot.models.user import Collection, CollectionStatus
from weschatbot.services.document.index_document_service import PipelineMilvusStore, \
    IndexDocumentWithoutConverterService
from weschatbot.utils.config import config
from weschatbot.utils.db import provide_session
from weschatbot.worker.celery_worker import celery_app

app = celery_app()

logger = logging.getLogger(__name__)


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
            logger.info(f"Running {func.__name__}; job run {job_id}")
            func(*args, **kwargs)
            status = "done"
            logger.info(f"Finished {func.__name__}; job run {job_id}")
        except Exception as e:
            logger.error(e)
            status = "failed"
            logger.error(f"Failed {func.__name__}; job run {job_id}")
        update(job_id, status)

    return wrapper


def update_collection_status(func):
    @provide_session
    def update(collection_id, status, session=None):
        status_entity = session.query(CollectionStatus).filter(CollectionStatus.name == status).one_or_none()
        if not status_entity:
            raise ValueError(f"Unknown status '{status}'. Please run command 'alembic upgrade head' to upgrade db.")
        collection = session.get(Collection, collection_id)
        collection.status = status_entity

    @wraps(func)
    def wrapper(collection_id, *args, **kwargs):
        try:
            update(collection_id, "running")
            logger.info(f"Running {func.__name__}; job run {collection_id}")
            func(collection_id, *args, **kwargs)
            status = "done"
            logger.info(f"Finished {func.__name__}; job run {collection_id}")
        except Exception as e:
            logger.error(e)
            status = "failed"
            logger.error(f"Failed {func.__name__}; job run {collection_id}")
        update(collection_id, status)

    return wrapper


@app.task(queue="index")
@update_collection_status
def index_collection_to_milvus(collection_id, collection_name):
    async def run_indexing():
        pipeline = PipelineMilvusStore(
            collection_name=collection_name,
            milvus_host=config["milvus"]["host"],
            milvus_port=config["milvus"]["port"]
        )
        indexer = IndexDocumentWithoutConverterService(
            converter=None,
            pipeline=pipeline,
            collection_name=collection_name,
            collection_id=collection_id
        )
        indexer.index()

    return asyncio.run(run_indexing())


@app.task(queue="convert")
def convert_document(document):
    logger.info(f"Start converting - Document ID {document['id']}, calling sub process")
    result = subprocess.run(
        ["weschatbot", "document", "convert", "--id", f"{document['id']}"],
        capture_output=True
    )
    if result.returncode != 0:
        logger.info(f"Sub process failed with code {result.returncode}")
        logger.info(f"Document ID {document['id']} is not converted.")
    logger.info(f"Done - Document ID {document['id']}")
