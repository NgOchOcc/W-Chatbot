from weschatbot.models.user import Query
from weschatbot.utils.db import provide_session


def make_query_result(rank, doc):
    # TODO
    return QueryResult(document_id=14, row_id=1, document_text=doc["text"], cosine_score=doc["score"], rank=rank,
                       collection_id=23, collection_name="test_collection")


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
