import asyncio
from random import Random
from rchain.client import RClient
from rchain.crypto import PrivateKey
from dataclasses import dataclass

@dataclass
class Transfer:
    sender: str
    recipient: str
    amount: int

class VaultDemoException(Exception):
    pass


def rand_int(rng: Random) -> int:
    return rng.randrange(0, 1 << 32)


def rand_rand(rng: Random) -> Random:
    return Random(rand_int(rng))


class AsyncRClient:

    def __init__(
            self,
            blocking_client: RClient,
            phlo_price: int = 1,
            phlo_limit: int = 1000000000):
        self.blocking_client = blocking_client
        self.phlo_price = phlo_price
        self.phlo_limit = phlo_limit

    async def deploy(self, key: PrivateKey, contract: str, ts=None):
        return await asyncio.get_running_loop().run_in_executor(
            None, self.blocking_client.deploy, key, contract, self.phlo_price,
            self.phlo_limit, ts)

    async def propose(self):
        return await asyncio.get_running_loop().run_in_executor(
            None, self.blocking_client.propose)

    async def get_data_at_deploy_id(self, deploy_id: bytes):
        return await asyncio.get_running_loop().run_in_executor(
            None, self.blocking_client.get_data_at_deploy_id, deploy_id)
