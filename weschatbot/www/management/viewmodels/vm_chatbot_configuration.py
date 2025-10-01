from weschatbot.www.management.model_vm import SingleViewModel
from weschatbot.www.management.utils import outside_url_for


class ViewModelChatbotConfiguration(SingleViewModel):
    list_fields = ["prompt", "collection", "similar_threshold", "temperature", "max_completion_tokens"]

    update_fields = ["prompt", "collection", "similar_threshold", "temperature", "max_completion_tokens"]
    add_fields = []
    detail_fields = ["id", "prompt", "collection", "similar_threshold", "temperature", "max_completion_tokens"]
    search_fields = ["collection"]

    disabled_view_models = ["add", "list"]

    actions = {
        "Update configuration": outside_url_for(".update_item")
    }
