from sqlalchemy import desc, func

from weschatbot.models.user import Query, ChatMessage
from weschatbot.utils.db import provide_session


def make_query_result(rank, doc):
    # TODO
    return QueryResult(document_id=14, row_id=doc["id"], document_text=doc["text"], cosine_score=doc["score"],
                       rank=rank,
                       collection_id=23, collection_name="test_collection")


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
            ).to_dict())

        return result
