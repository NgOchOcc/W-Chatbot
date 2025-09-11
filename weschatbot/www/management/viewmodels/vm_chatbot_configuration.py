from weschatbot.www.management.model_vm import SingleViewModel
from weschatbot.www.management.utils import outside_url_for


class ViewModelChatbotConfiguration(SingleViewModel):
    list_fields = ["prompt", "collection", "similar_threshold"]

    update_fields = ["prompt", "collection", "similar_threshold"]
    add_fields = []
    detail_fields = ["id", "prompt", "collection", "similar_threshold"]
    search_fields = ["collection"]

    disabled_view_models = ["add", "list"]

    actions = {
        "Update configuration": outside_url_for(".update_item")
    }
