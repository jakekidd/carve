import os
import json
import requests
from dotenv import load_dotenv
from web3 import Web3

# Load environment variables
load_dotenv()
INFURA_URL = os.getenv("INFURA_URL")
COINBASE_RELAYER_API_KEY = os.getenv("COINBASE_RELAYER_API_KEY")
TREE_CONTRACT_ADDRESS = os.getenv("TREE_CONTRACT_ADDRESS")

# Load ABI from artifacts folder
with open("./artifacts/Tree.sol/Tree.json", "r") as abi_file:
    TREE_ABI = json.load(abi_file)["abi"]

# Initialize Web3 instance
w3 = Web3(Web3.HTTPProvider(INFURA_URL))
tree_contract = w3.eth.contract(address=TREE_CONTRACT_ADDRESS, abi=TREE_ABI)

# TODO: Not sure if this API usage is correct
class CarveAPI:
    @staticmethod
    def get_carving(carving_id: str):
        """Retrieve a carving's message from the contract."""
        try:
            carving_id_bytes = bytes.fromhex(carving_id)
            properties, message = tree_contract.functions.read(carving_id_bytes).call()
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
    def send_carving(carving_id: str, properties: str, message: str, signature: str):
        """Send a 'carve' transaction using Coinbase Relayer API."""
        url = "https://api.coinbase.com/v2/relayer/send"
        headers = {"Authorization": f"Bearer {COINBASE_RELAYER_API_KEY}", "Content-Type": "application/json"}
        data = {
            "to": TREE_CONTRACT_ADDRESS,
            "data": tree_contract.encodeABI(
                fn_name="carve",
                args=[bytes.fromhex(carving_id), bytes.fromhex(properties), message, bytes.fromhex(signature)]
            ),
            "gas": "500000",
            "value": "0"
        }
        response = requests.post(url, headers=headers, json=data)
        return response.json()
