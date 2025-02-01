from ssm_parameter_store import EC2ParameterStore

class ParameterHandler:
    user_id_salt : str = None
    carving_id_salt : str = None
    admin_key : str = None
    stripe_api_key : str = None
    max_index_failures : int = None
    carving_length_limit : int = None
    ssm_refresh_interval : int = None

    def update_from_ssm(self):
        store = EC2ParameterStore()
        parameters = store.get_parameters_with_hierarchy('/', decrypt=True)
        self.stripe_api_key = parameters["secrets"]["stripe_api_key"]
        self.user_id_salt = parameters["secrets"]["user_id_salt"]
        self.carving_id_salt = parameters["secrets"]["carving_id_salt"]
        self.admin_key = parameters["secrets"]["admin_key"]
        self.max_index_failures = int(parameters["config"]["max_index_failures"])
        self.carving_length_limit = int(parameters["config"]["carving_length_limit"])
        self.ssm_refresh_interval = int(parameters["config"]["ssm_refresh_interval"])

    def __init__(self):
        self.update_from_ssm()