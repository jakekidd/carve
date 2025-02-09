import os
import json
from threading import Lock
from time import sleep

import requests
from hexbytes import HexBytes
import logging
from typing import Dict, List
from queue import Queue

from web3 import Web3
from web3.contract import Contract
from web3.datastructures import AttributeDict
from web3.middleware import SignAndSendRawMiddlewareBuilder

from app import app, parameters, db, ExistingCarving
from eth_account import Account
from eth_account.signers.local import LocalAccount

# Initialize Web3 instance
w3 : Web3 = Web3(Web3.HTTPProvider(parameters.infura_url + parameters.infura_api_key))
tree_contract : Contract = w3.eth.contract(address=parameters.tree_contract_address,
                                abi=json.load(open("./artifacts/Tree.sol/Tree.json", "r"))["abi"])
account: LocalAccount = Account.from_key(parameters.eth_private_key)
w3.middleware_onion.inject(SignAndSendRawMiddlewareBuilder.build(account), layer=0)


def generate_user_id(email: str) -> HexBytes:
    return Web3.solidity_keccak(["string", "string"], [email, parameters.user_id_salt])

def generate_carving_id(user_id: HexBytes, index: int) -> HexBytes:
    return Web3.solidity_keccak(["bytes32", "uint32", "string"], [user_id, index, parameters.carving_id_salt])


class CarveAPI:
    next_index : Dict[HexBytes, int] = {}
    task_queue = Queue()
    _lock : Lock = Lock()

    def __init__(self):
        self.update_existing_carvings()

    def calculate_next_index(self, user_id: HexBytes):
        failed_attempts = 0
        current_index = self.next_index.get(user_id, 0)
        with self._lock:
            while failed_attempts < parameters.max_index_failures:
                if ExistingCarving.query.filter_by(carving_id=generate_carving_id(user_id, current_index)).first():
                    failed_attempts = 0
                else:
                    failed_attempts += 1
                current_index += 1
        self.next_index[user_id] = max(current_index - failed_attempts, self.next_index.get(user_id, 0))

    def get_carving(self, carving_id: HexBytes):
        return ExistingCarving.query.filter_by(carving_id=carving_id.to_0x_hex()).first()
        #carving = ExistingCarving.query.filter_by(carving_id=carving_id.to_0x_hex()).first()
        #if not carving:
        #"""Retrieve a carving's message from the contract."""
        #try:
        #    properties, message = tree_contract.functions.read(carving_id).call()
        #    return {"carving_id": carving_id, "properties": properties.hex(), "message": message}
        #except Exception as e:
        #    return {"error": str(e)}


    def get_public_carvings(self):
        """Retrieve all public carving IDs from the gallery."""
        try:
            carvings = tree_contract.functions.peruse().call()
            return [c.hex() for c in carvings]
        except Exception as e:
            return {"error": str(e)}


    def make_carving(self, carving_id: HexBytes, properties: HexBytes, message: str) -> HexBytes:
        #payload_hash =  Web3.solidity_keccak(["bytes32", "bytes32", "string"], [carving_id, properties, message])
        #signature = account.unsafe_sign_hash(payload_hash)
        carving_txn = tree_contract.functions.carve(carving_id, properties, message, b"").transact({"from": account.address})
        with self._lock:
            record = ExistingCarving(carving_id=carving_id.to_0x_hex(),
                                     carving_txn=carving_txn.to_0x_hex(),
                                     carving_from="",  # carving.args.carvingFrom.hex(),
                                     carving_to="",  # carving.args.carvingTo.hex(),
                                     carving_text=message,
                                     parameters=properties.to_0x_hex())
            db.session.add(record)
            db.session.commit()
        return carving_txn

    def update_existing_carvings(self):
        """Retrieve all carvings from eth.get_logs."""
        try:
            with app.app_context():
                store_events = tree_contract.events.CarvingStored().get_logs(from_block="earliest")
                sleep(2)
                delete_events = tree_contract.events.CarvingDeleted().get_logs(from_block="earliest")
                deleted_ids = [x.args.carvingId for x in delete_events]
                existing_carvings = [x for x in store_events if x.args.carvingId not in deleted_ids]
                with self._lock:
                    ExistingCarving.query.delete()
                    #app.logger.debug(f"Deleted rows: {}")
                    for carving in existing_carvings:
                        record = ExistingCarving(carving_id=HexBytes(carving.args.carvingId.hex()).to_0x_hex(),
                                                 carving_txn=carving.transactionHash.to_0x_hex(),
                                                 carving_from="",#carving.args.carvingFrom,
                                                 carving_to="",#carving.args.carvingTo,
                                                 carving_text=carving.args.message,
                                                 parameters=HexBytes(carving.args.properties).to_0x_hex())
                        db.session.add(record)
                    db.session.commit()
                for user_id in self.next_index.keys():
                    self.calculate_next_index(user_id)
        except Exception as e:
            print(f"error in get_all_carvings: {str(e)}")
