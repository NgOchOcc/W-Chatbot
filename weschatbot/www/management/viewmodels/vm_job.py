from weschatbot.www.management.model_vm import ViewModel


class ViewModelJob(ViewModel):
    list_fields = ["id", "name", "class_name", "status"]
    update_fields = ["class_name", "status", "params"]
    add_fields = ["name", "class_name", "params", "status"]
    detail_fields = ["name", "class_name", "params"]
    search_fields = ["name", "class_name", "params", "status"]
