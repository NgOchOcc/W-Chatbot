from pymilvus import connections

from weschatbot.ambiguity.logger import ParquetLogger
from weschatbot.schemas.embedding import RetrievalConfig
from weschatbot.services.explore_services.explore_retrieve_service import ExploreRetrieveService
from weschatbot.utils.config import config

if __name__ == '__main__':
    connections.connect("default", host=config["milvus"]["host"], port=int(config["milvus"]["port"]))

    question_file_path = "data/questions_1.txt"
    file_logger = ParquetLogger(filename="pipeline_log_elbow_steepness_entropy.parquet")
    explore_retrieve_service = ExploreRetrieveService(
        logger=file_logger
    )

    retrieval_config = RetrievalConfig(
        collection_name="test_vllm_v9",
        milvus_host=config["milvus"]["host"],
        milvus_port=int(config["milvus"]["port"]),
        embedding_mode=config['embedding_model']['mode'],
        embedding_model=config['embedding_model']['model'],
        vllm_base_url=config['embedding_model']['vllm_embedding_url'],
        search_limit=int(config['retrieval']['search_limit']),
        metric_type=config['retrieval']['metrics']
    )

    explore_retrieve_service.collect_data(question_file_path, retrieval_config)
