from weschatbot.www.management.model_vm import SingleViewModel
from weschatbot.www.management.utils import outside_url_for


class ViewModelChatbotConfiguration(SingleViewModel):
    list_fields = ["prompt", "collection", "similar_threshold", "temperature", "max_completion_tokens",
                   "limit_interval_seconds", "limit"]

    update_fields = ["prompt", "collection", "similar_threshold", "temperature", "max_completion_tokens",
                     "limit_interval_seconds", "limit", "summary_prompt", "analytic_topic_prompt"]
    add_fields = []
    detail_fields = ["id", "prompt", "collection", "similar_threshold", "temperature", "max_completion_tokens",
                     "limit_interval_seconds", "limit",
                     "summary_prompt", "analytic_topic_prompt"]
    search_fields = ["collection"]

    disabled_view_models = ["add", "list"]

    actions = {
        "Update configuration": outside_url_for(".update_item")
    }
