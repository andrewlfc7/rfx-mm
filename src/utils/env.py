import os
from dotenv import load_dotenv

load_dotenv()

def get_env_vars():
    """Get environment variables"""
    return {
        'USER_WALLET_ADDRESS': os.getenv('USER_WALLET_ADDRESS'),
        'PRIVATE_KEY': os.getenv('PRIVATE_KEY')
            }