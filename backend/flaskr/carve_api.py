import os
import json
import requests
from web3 import Web3
from app import parameters
from eth_account import Account
from eth_account.signers.local import LocalAccount

# Initialize Web3 instance
w3 = Web3(Web3.HTTPProvider(parameters.infura_url + parameters.infura_api_key))
tree_contract = w3.eth.contract(address=parameters.tree_contract_address,
                                abi=json.load(open("./artifacts/Tree.sol/Tree.json", "r"))["abi"])
account: LocalAccount = Account.from_key(parameters.eth_private_key)

# TODO: Not sure if this API usage is correct
class CarveAPI:
    @staticmethod
    def generate_user_id(email: str) -> bytes:
        return Web3.solidity_keccak(["string", "string"], [email, parameters.user_id_salt])

    @staticmethod
    def generate_carving_id(user_id: bytes, index: int) -> bytes:
        return Web3.solidity_keccak(["bytes32", "uint32", "string"], [user_id, index, parameters.carving_id_salt])

    @staticmethod
    def get_carving(carving_id: bytes):
        """Retrieve a carving's message from the contract."""
        try:
            properties, message = tree_contract.functions.read(carving_id).call()
            return {"carving_id": carving_id, "properties": properties.hex(), "message": message}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_public_carvings():
        """Retrieve all public carving IDs from the gallery."""
        try:
            carvings = tree_contract.functions.peruse().call()
            return [c.hex() for c in carvings]
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def make_carving(carving_id: bytes, properties: bytes, message: str):
        #payload_hash =  Web3.solidity_keccak(["bytes32", "bytes32", "string"], [carving_id, properties, message])
        #signature = account.unsafe_sign_hash(payload_hash)
        return tree_contract.functions.carve(carving_id, carving_id, message, b"").transact({"from": account.address})
