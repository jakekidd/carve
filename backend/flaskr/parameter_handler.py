from ssm_parameter_store import EC2ParameterStore
import json
from hexbytes import HexBytes


class ParameterHandler:
    user_id_salt : str = None
    carving_id_salt : str = None
    admin_key : str = None
    stripe_api_key : str = None
    stripe_webhook_key : str = None
    max_index_failures : int = None
    carving_from_to_limit : int = None
    carving_length_limit : int = None
    ssm_refresh_interval : int = None
    infura_url : str = None
    infura_api_key : str = None
    tree_contract_address : bytes = None
    eth_private_key : bytes = None
    stripe_price_id : str = None
    payment_success_url : str = None
    payment_cancel_url : str
    sender_email : str = None
    gmail_token : dict = None
    carvings_sheet_id : str = None

    def update_from_ssm(self):
        store = EC2ParameterStore(region_name="us-east-1")
        parameters = store.get_parameters_with_hierarchy('/', decrypt=True)
        self.stripe_api_key = parameters["secrets"]["stripe_api_key"]
        self.stripe_webhook_key = parameters["secrets"]["stripe_webhook_key"]
        self.user_id_salt = parameters["secrets"]["user_id_salt"]
        self.carving_id_salt = parameters["secrets"]["carving_id_salt"]
        self.admin_key = parameters["secrets"]["admin_key"]
        self.infura_api_key = parameters["secrets"]["infura_api_key"]
        self.eth_private_key = HexBytes(parameters["secrets"]["eth_private_key"])
        self.gmail_token = json.loads(parameters["secrets"]["gmail_token"])
        self.carvings_sheet_id = parameters["secrets"]["carvings_sheet_id"]

        self.max_index_failures = int(parameters["config"]["max_index_failures"])
        self.carving_from_to_limit = int(parameters["config"]["carving_from_to_limit"])
        self.carving_length_limit = int(parameters["config"]["carving_length_limit"])
        self.ssm_refresh_interval = int(parameters["config"]["ssm_refresh_interval"])
        self.infura_url = parameters["config"]["infura_url"]
        self.tree_contract_address = HexBytes(parameters["config"]["tree_contract_address"])
        self.stripe_price_id = parameters["config"]["stripe_price_id"]
        self.payment_success_url = parameters["config"]["payment_success_url"]
        self.payment_cancel_url = parameters["config"]["payment_cancel_url"]
        self.sender_email = parameters["config"]["sender_email"]

    def upload_changes(self):
        store = EC2ParameterStore(region_name="us-east-1")
        store.put_parameter(name="/secrets/gmail_token", value=json.dumps(self.gmail_token), value_type="SecureString", Overwrite=True)

    def __init__(self):
        self.update_from_ssm()