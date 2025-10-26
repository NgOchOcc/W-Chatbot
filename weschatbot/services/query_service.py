import functools
import inspect
import pickle

import redis
from sqlalchemy import desc, func

from weschatbot.models.user import Query
from weschatbot.services.vllm_llm_service import VLLMService
from weschatbot.utils.config import config
from weschatbot.utils.db import provide_session


def make_query_result(rank, doc, collection_id):
    # TODO
    return QueryResult(document_id=14, row_id=doc["id"], document_text=doc["text"], cosine_score=doc["score"],
                       rank=rank,
                       collection_id=collection_id, collection_name="test_collection")


def redis_cache(expire_seconds=3600, key_args=None, redis_url="redis://localhost:6379/0"):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            r = redis.Redis.from_url(redis_url)

            sig = inspect.signature(fn)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            arg_map = bound.arguments

            key_parts = [fn.__name__]
            if key_args:
                for k in key_args:
                    val = arg_map.get(k)
                    key_parts.append(f"{k}={val}")
            redis_key = "cache:" + "|".join(key_parts)

            cached = r.get(redis_key)
            if cached:
                return pickle.loads(cached)

            result = fn(*args, **kwargs)
            r.setex(redis_key, expire_seconds, pickle.dumps(result))
            return result

        return wrapper

    return decorator


class Question:
    def __init__(self, text, created_date, message_id, query_id):
        self.text = text
        self.created_date = created_date
        self.message_id = message_id
        self.query_id = query_id

    def to_dict(self):
        return {
            "text": self.text,
            "created_date": self.created_date,
            "message_id": self.message_id,
            "query_id": self.query_id,
        }


class QueryResultSummary:
    def __init__(self, row_id, count, v_avg, v_min, v_max, first_seen, last_seen, query_ids, message_ids,
                 document_text, questions):
        self.row_id = row_id
        self.count = count
        self.v_avg = v_avg
        self.v_min = v_min
        self.v_max = v_max
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.query_ids = query_ids
        self.message_ids = message_ids,
        self.document_text = document_text
        self.questions = questions

    def to_dict(self):
        return {
            "row_id": str(self.row_id),
            "document_text": self.document_text,
            "count": self.count,
            "v_avg": self.v_avg,
            "v_min": self.v_min,
            "v_max": self.v_max,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "query_ids": self.query_ids,
            "message_ids": self.message_ids,
            "questions": self.questions
        }


class QueryResult:
    def __init__(self, document_id, row_id, document_text, cosine_score, rank, collection_id, collection_name):
        self.document_id = document_id
        self.row_id = row_id
        self.document_text = document_text
        self.cosine_score = cosine_score
        self.rank = rank
        self.collection_id = collection_id
        self.collection_name = collection_name


class QueryService:
    vllm_service = VLLMService(config["vllm"]["base_url"], config["vllm"]["model"])

    @provide_session
    def add_query_result_for_message(self, list_query_results, message_id, session=None):
        for query_result in list_query_results:
            query = Query(message_id=message_id,
                          document_id=query_result.document_id,
                          row_id=query_result.row_id,
                          document_text=query_result.document_text,
                          cosine_score=query_result.cosine_score,
                          rank=query_result.rank,
                          collection_id=query_result.collection_id)
            session.add(query)

    @provide_session
    def get_query_results_by_date(self, from_date, to_date, page=1, page_size=20, message_id=None, session=None):
        query = session.query(Query).filter(
            Query.modified_date >= from_date,  # noqa
            Query.modified_date <= to_date  # noqa
        )

        if message_id:
            query = query.filter(Query.message_id == message_id)

        total = query.count()

        results = query.offset((page - 1) * page_size).limit(page_size).all()

        return [x.to_dict() for x in results], page, page_size, total, message_id

    @provide_session
    def summary_query_results(self, from_date, to_date, session=None):
        stats = self.summary_query_by_date(from_date, to_date, session=session)

        result = []

        for row in stats:
            query_ids = [int(x) for x in row.query_ids.split(",") if x]

            queries = (
                session.query(Query)
                .filter(Query.id.in_(query_ids))
                .all()
            )

            questions = []
            for q in queries:
                if q.message and q.message.content:
                    questions.append(Question(
                        text=q.message.content,
                        created_date=q.modified_date.isoformat(),
                        message_id=q.message_id,
                        query_id=q.id
                    ).to_dict())

            result.append(QueryResultSummary(
                row_id=row.row_id,
                count=row.count,
                v_avg=float(row.avg),
                v_min=float(row.min),
                v_max=float(row.max),
                first_seen=row.first_seen.isoformat(),
                last_seen=row.last_seen.isoformat(),
                query_ids=query_ids,
                message_ids=[int(x) for x in row.message_ids.split(",") if x],
                document_text=row.document_text,
                questions=questions
            ))

        return result

    @provide_session
    def summary_query_by_date(self, from_date, to_date, session=None):
        stats = (
            session.query(
                Query.row_id.label("row_id"),
                func.min(Query.document_text).label("document_text"),
                func.count(Query.id).label("count"),
                func.avg(Query.cosine_score).label("avg"),
                func.min(Query.cosine_score).label("min"),
                func.max(Query.cosine_score).label("max"),
                func.group_concat(Query.id).label("query_ids"),
                func.group_concat(Query.message_id).label("message_ids"),
                func.min(Query.modified_date).label("first_seen"),  # noqa
                func.max(Query.modified_date).label("last_seen")  # noqa
            )
            .filter(Query.modified_date >= from_date, Query.modified_date <= to_date)  # noqa
            .group_by(Query.row_id)
            .order_by(desc("count"))
        ).all()

        return stats

    @staticmethod
    def split_documents(documents, max_tokens: int):
        groups = []
        current_group = []
        current_token_sum = 0

        for doc in documents:
            if doc.number_of_tokens > max_tokens:
                groups.append([doc])
                continue

            if current_token_sum + doc.number_of_tokens <= max_tokens:
                current_group.append(doc)
                current_token_sum += doc.number_of_tokens
            else:
                groups.append(current_group)
                current_group = [doc]
                current_token_sum = doc.number_of_tokens

        if current_group:
            groups.append(current_group)

        return groups

    @redis_cache(expire_seconds=300, key_args=["from_date", "to_date"],
                 redis_url=f"redis://{config['redis']['host']}:{config['redis']['port']}/0")
    @provide_session
    def analyze_query_results(self, from_date, to_date, max_tokens=5120, session=None):
        # TODO refactor
        stats = self.summary_query_by_date(from_date, to_date, session=session)

        documents = [QueryResultWithLLM(row.document_text, row.count).get_number_tokens(vllm_service=self.vllm_service)
                     for row in stats]

        grouped_documents = self.split_documents(documents, max_tokens=max_tokens)
        summaries = [self.get_summary(self.vllm_service, "\n".join([y.document_text for y in x])) for x in
                     grouped_documents]
        if len(summaries) == 1:
            return self.get_topics(self.vllm_service, summaries[0])
        return self.get_topics(self.vllm_service, "\n".join(summaries))

    @staticmethod
    def get_topics(vllm_service, text):
        return vllm_service.sync_get_topics(text)

    @staticmethod
    def get_summary(vllm_service, text):
        summary = vllm_service.sync_get_summary(text)
        return summary


class QueryResultWithLLM:
    def __init__(self, document_text, count):
        self.document_text = document_text
        self.count = count
        self.number_of_tokens = 0
        self.summary = None

    def get_number_tokens(self, vllm_service):
        self.number_of_tokens = vllm_service.sync_count_tokens(self.document_text)
        return self
