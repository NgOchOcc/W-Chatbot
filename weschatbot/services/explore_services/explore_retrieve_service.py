import asyncio

from tenacity import retry, stop_after_attempt, RetryError, wait_fixed

from weschatbot.ambiguity.ambiguity_pipeline import CosineFilter, SoftmaxEntropy, Clustering, ClusterLabeling, Decision, \
    AmbiguityPipeline
from weschatbot.ambiguity.chunk import Chunk
from weschatbot.ambiguity.elbow_detection import ElbowDetection
from weschatbot.ambiguity.logger import CSVLogger
from weschatbot.ambiguity.steepness import Steepness
from weschatbot.log.logging_mixin import LoggingMixin
from weschatbot.services.retrieve_service import Retriever


@retry(stop=stop_after_attempt(3), wait=wait_fixed(3), reraise=True)
async def retrieve_questions(retriever, question, search_limit):
    return await retriever.retrieve(query=question, search_limit=search_limit)


class ExploreRetrieveService(LoggingMixin):
    def __init__(self,
                 filter_task=CosineFilter(threshold=0.4),
                 entropy_task=SoftmaxEntropy(),
                 elbow_task=ElbowDetection(alpha=0.5, min_index=1, sigma_factor=0.4),
                 steepness_task=Steepness(alpha=0.8, sigma_factor=0.25),
                 cluster_task=Clustering(n_clusters=2),
                 labeling_task=ClusterLabeling(),
                 decision_task=Decision(),
                 logger=CSVLogger()):
        self.ambiguity_pipeline = AmbiguityPipeline(
            filter_task=filter_task,
            entropy_task=entropy_task,
            elbow_task=elbow_task,
            steepness_task=steepness_task,
            cluster_task=cluster_task,
            labeling_task=labeling_task,
            decision_task=decision_task,
            logger=logger
        )

    async def async_collect_data(self, question_file_path, retrieval_config):
        retriever = Retriever(retrieval_config)

        with open(question_file_path, 'r') as f:
            questions = f.readlines()

        for question_id, question in enumerate(questions):
            try:
                retrieved_docs = await retrieve_questions(retriever, question=question,
                                                          search_limit=30)

                chunks = [
                    Chunk(question_id=question_id, question=question, content=doc["text"], vector=doc["embedding"],
                          score=doc["score"]) for doc
                    in retrieved_docs]
                self.ambiguity_pipeline.run(chunks)
            except RetryError as e:
                self.log.warning(f"Error in question: {question_id}")

    def collect_data(self, question_file_path, retrieval_config):
        asyncio.run(self.async_collect_data(question_file_path, retrieval_config))
