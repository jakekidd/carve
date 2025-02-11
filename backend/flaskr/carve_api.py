import json
from threading import Lock
from time import sleep

from hexbytes import HexBytes
from typing import Dict, List
from queue import Queue

from sqlalchemy.dialects.mysql import insert
from web3 import Web3
from web3.contract import Contract
from web3.datastructures import AttributeDict
from web3.exceptions import ContractCustomError
from web3.middleware import SignAndSendRawMiddlewareBuilder

from app import app, parameters, db, ExistingCarving, email_handler
from eth_account import Account
from eth_account.signers.local import LocalAccount


class CarveAPI:
    def __init__(self):
        app.logger.debug("Initializing CarveAPI.")
        self.next_index: Dict[HexBytes, int] = {}
        self.task_queue = Queue()
        #self._lock: Lock = Lock()
        self.w3: Web3 = Web3(Web3.HTTPProvider(parameters.infura_url + parameters.infura_api_key))
        self.tree_contract: Contract = self.w3.eth.contract(address=parameters.tree_contract_address,
                                                            abi=json.load(open("./artifacts/Tree.sol/Tree.json", "r"))["abi"],
                                                            decode_tuples=True)
        self.op_account: LocalAccount = Account.from_key(parameters.eth_private_key)
        self.w3.middleware_onion.inject(SignAndSendRawMiddlewareBuilder.build(self.op_account), layer=0)
        self.update_existing_carvings()
    
    @staticmethod
    def generate_user_id(email: str) -> HexBytes:
        return Web3.solidity_keccak(["string", "string"], [email, parameters.user_id_salt])
    
    @staticmethod
    def generate_carving_id(user_id: HexBytes, index: int) -> HexBytes:
        return Web3.solidity_keccak(["bytes32", "uint32", "string"], [user_id, index, parameters.carving_id_salt])
    
    def id_is_used(self, carving_id: HexBytes) -> bool:
        with app.app_context():
            if ExistingCarving.query.filter_by(carving_id=carving_id.to_0x_hex()).first():
                return True
            try:
                self.tree_contract.functions.read(carving_id).call()
                return True
            except ContractCustomError:
                return False
    
    def get_next_id_for_email(self, email: str) -> HexBytes:
        user_id = self.generate_user_id(email)
        self.next_index.setdefault(user_id, 0)
        while self.id_is_used(self.generate_carving_id(user_id, self.next_index[user_id])):
            self.next_index[user_id] += 1
        return self.generate_carving_id(user_id, self.next_index[user_id])
    
    @staticmethod
    def get_carving(carving_id: HexBytes) -> ExistingCarving:
        return ExistingCarving.query.filter_by(carving_id=carving_id.to_0x_hex()).first()
    
    def get_public_carving_ids(self) -> List[HexBytes]:
        try:
            carvings = self.tree_contract.functions.peruse().call()
            return [HexBytes(c) for c in carvings]
        except Exception as e:
            app.logger.error(f"Error while perusing: {str(e)}")
            return []
    
    def make_carving(self, carving_id: HexBytes, carving_to: str, carving_from: str, carving_message: str, carving_properties: HexBytes) -> HexBytes:
        # payload_hash =  Web3.solidity_keccak(["bytes32", "bytes32", "string"], [carving_id, properties, message])
        # signature = account.unsafe_sign_hash(payload_hash)
        if not carving_message:
            raise ValueError("Carving message cannot be empty.")
        if len(carving_id) != 32:
            raise ValueError("Carving ID must be 32 bytes long.")
        carving_to = carving_to[:parameters.carving_from_to_limit]
        carving_from = carving_from[:parameters.carving_from_to_limit]
        carving_message = carving_message[:parameters.carving_length_limit]
        carving_properties = HexBytes(HexBytes("00" * 31) + carving_properties)[-31:]
        carving_txn = self.tree_contract.functions.carve(carvingId=carving_id,
                                                         carvingTo=carving_to,
                                                         carvingFrom=carving_from,
                                                         carvingMessage=carving_message,
                                                         carvingProperties=carving_properties).transact({"from": self.op_account.address})
        with app.app_context():#, self._lock:
            db.session.execute(insert(ExistingCarving).values([{
                    "carving_id"        : carving_id.to_0x_hex(),
                    "carving_txn"       : carving_txn.to_0x_hex(),
                    "carving_to"        : carving_to,
                    "carving_from"      : carving_from,
                    "carving_message"   : carving_message,
                    "carving_properties": carving_properties.to_0x_hex()}]))
            db.session.commit()
            email_handler.db_to_sheets()
            return carving_txn
    
    def update_existing_carvings(self):
        try:
            store_events = self.tree_contract.events.CarvingStored().get_logs(from_block="earliest")
            sleep(1)
            delete_events = self.tree_contract.events.CarvingDeleted().get_logs(from_block="earliest")
            deleted_ids = set(x.args.carvingId for x in delete_events)
            existing_carvings = [x for x in store_events if x.args.carvingId not in deleted_ids]
            with app.app_context():#, self._lock:
                ExistingCarving.query.delete()  #TODO: less ugly, separate process
                if len(existing_carvings):
                    db.session.execute(insert(ExistingCarving).values([{
                            "carving_id"        : HexBytes(x.args.carvingId).to_0x_hex(),
                            "carving_txn"       : x.transactionHash.to_0x_hex(),
                            "carving_to"        : x.args["to"],
                            "carving_from"      : x.args["from"],
                            "carving_message"   : x.args["message"],
                            "carving_properties": HexBytes(x.args.properties).to_0x_hex()} for x in existing_carvings]))
                if len(delete_events):
                    db.session.execute(insert(ExistingCarving).values([{
                            "carving_id"        : HexBytes(x.args.carvingId).to_0x_hex(),
                            "carving_txn"       : x.transactionHash.to_0x_hex(),
                            "carving_to"        : None,
                            "carving_from"      : None,
                            "carving_message"   : None,
                            "carving_properties": HexBytes("00" * 31).to_0x_hex()} for x in delete_events]))
                app.logger.debug(f"Updated existing carvings, totals: {len(existing_carvings)} created, {len(deleted_ids)} deleted.")
                db.session.commit()
                email_handler.db_to_sheets()
        except Exception as e:
            print(f"error in update_existing_carvings: {str(e)}")
