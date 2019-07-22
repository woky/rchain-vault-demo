import sys
import time
import grpc
from rchain.crypto import PrivateKey
from rchain.client import RClient
from rchain.vault import VaultAPI, VaultAPIException

if len(sys.argv) != 3:
    print(f'Usage {sys.argv[0]} <rpc_addr> <rev_addr>', file=sys.stderr)
    sys.exit(1)

rpc_addr = sys.argv[1]
rev_addr = sys.argv[2]

key = PrivateKey.generate()
with grpc.insecure_channel(rpc_addr) as channel:
    client = RClient(channel)
    vault_api = VaultAPI(client, key)
    deploy_id = vault_api.deploy_get_balance(rev_addr)
    while True:
        try:
            bal = vault_api.get_balance_from_deploy_id(deploy_id)
            print(bal)
        except VaultAPIException as e:
            print('ERROR:', str(e))
        time.sleep(5)
