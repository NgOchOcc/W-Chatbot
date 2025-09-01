import logging

from weschatbot.models.collection import CollectionStatus, Collection
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


# @app.task
# @update_job_status
# def index_documents():
#     converter = DocumentConverter()
#     pipeline = PipelineMilvusStore(collection_name=config["core"]["milvus_collection_name"],
#                                    milvus_host=config["milvus"]["host"],
#                                    milvus_port=config["milvus"]["port"])
#     indexer = IndexDocumentService(converter=converter, pipeline=pipeline)
#     indexer.index()


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
            logging.info(f"Running {func.__name__}; job run {collection_id}")
            func(collection_id, *args, **kwargs)
            status = "done"
            logging.info(f"Finished {func.__name__}; job run {collection_id}")
        except Exception as e:
            logging.error(e)
            status = "failed"
            logging.error(f"Failed {func.__name__}; job run {collection_id}")
        update(collection_id, status)

    return wrapper


@app.task
@update_collection_status
def index_collection_to_milvus(collection_id, collection_name):
    import asyncio

    async def run_indexing():
        converter = DocumentConverter()
        pipeline = PipelineMilvusStore(
            collection_name=collection_name,
            milvus_host=config["milvus"]["host"],
            milvus_port=config["milvus"]["port"]
        )
        indexer = IndexDocumentService(
            converter=converter,
            pipeline=pipeline,
            collection_name=collection_name,
            collection_id=collection_id
        )
        indexer.index()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_indexing())
