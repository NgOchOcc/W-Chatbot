from weschatbot.www.management.model_vm import ViewModel


class ViewModelChat(ViewModel):
    list_fields = ["id", "uuid", "name", "user"]
    update_fields = ["name"]
    add_fields = []
    detail_fields = ["id", "name", "user", "messages"]
    search_fields = ["name"]

    disabled_view_models = ["add", "update"]
