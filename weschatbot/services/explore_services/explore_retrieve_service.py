import asyncio

from weschatbot.ambiguity.ambiguity_pipeline import CosineFilter, EntropyCheck, Clustering, ClusterLabeling, Decision, \
    AmbiguityPipeline
from weschatbot.ambiguity.chunk import Chunk
from weschatbot.ambiguity.logger import CSVLogger
from weschatbot.services.retrieve_service import Retriever


class ExploreRetrieveService:
    def __init__(self,
                 filter_task=CosineFilter(threshold=0.7),
                 entropy_task=EntropyCheck(),
                 cluster_task=Clustering(n_clusters=2),
                 labeling_task=ClusterLabeling(),
                 decision_task=Decision(),
                 logger=CSVLogger()):
        self.ambiguity_pipeline = AmbiguityPipeline(filter_task=filter_task, entropy_task=entropy_task,
                                                    cluster_task=cluster_task, labeling_task=labeling_task,
                                                    decision_task=decision_task, logger=logger)

    async def async_collect_data(self, question_file_path, retrieval_config):
        retriever = Retriever(retrieval_config)

        with open(question_file_path, 'r') as f:
            questions = f.readlines()

        for question_id, question in enumerate(questions):
            retrieved_docs = await retriever.retrieve(query=question, search_limit=30)
            chunks = [Chunk(question_id=question_id, question=question, content=doc["text"], vector=doc["embedding"], score=doc["score"]) for doc
                      in retrieved_docs]
            self.ambiguity_pipeline.run(chunks)

    def collect_data(self, question_file_path, retrieval_config):
        asyncio.run(self.async_collect_data(question_file_path, retrieval_config))
