from weschatbot.www.management.model_vm import ViewModel


class ViewModelPermission(ViewModel):
    list_fields = ["id", "name", "roles"]
    update_fields = ["name"]
    add_fields = ["name"]
    detail_fields = ["id", "name", "roles"]
    search_fields = ["name"]
