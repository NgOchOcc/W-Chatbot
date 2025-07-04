from weschatbot.www.management.model_vm import ViewModel


class ViewModelRole(ViewModel):
    list_fields = ["id", "name", "permissions"]
    update_fields = ["name", "permissions"]
    add_fields = ["name", "permissions"]
    detail_fields = ["id", "name", "permissions"]
    search_fields = ["name"]
