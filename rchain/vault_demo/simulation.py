import random
import asyncio
import logging
from typing import List
from dataclasses import dataclass

import grpc

from rchain.crypto import PrivateKey
from rchain.client import RClient
from rchain.vault import VaultAPI

from .vault_user import VaultUser
from .phonetic_names import PhoneticNames
from .util import randseed

@dataclass
class SimulationConfig:
    vault_user_count: int = 5
    seed: int = None

async def _run_with_channels(self, config: SimulationConfig, rpc_channels):
    pass

async def main():
    with grpc.insecure_channel('172.27.0.2:40401') as c:
        client = RClient(c)
        rand = random.Random(37)

        user_count = 5
        user_initial_balance = 100000
        user_names = PhoneticNames(max_index=(user_count - 1), sep='_')

        vault_users_addrs = [None] * user_count
        vault_users = [None] * user_count

        for i in range(0, user_count):
            u = VaultUser(
                user_names[i].upper(),
                client,
                vault_users_addrs,
                seed=randseed(rand))
            vault_users[i] = u
            vault_users_addrs[i] = u.key.get_public_key().get_address()

        admin_key = PrivateKey.generate()
        admin_vault_api = VaultAPI(client, admin_key)
        admin_vault_api.create_genesis_vault(
            None, user_count * user_initial_balance)

        for user in vault_users:
            addr = user.key.get_public_key().get_address()
            admin_vault_api.deploy_transfer(None, addr, user_initial_balance)
            user.set_balance(user_initial_balance)
        client.propose()

        await vault_users[0].make_transfers()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)8s %(name)s %(message)s')
    asyncio.run(main())
