import random
import asyncio
import logging
from typing import List

import grpc

from rchain.crypto import PrivateKey
from rchain.client import RClient
from rchain.vault import VaultAPI

from .user import User


class SimulationConfig:
    rpc_addrs: List[str]
    initial_user_balance: int = 100000,
    users_per_node_mean: float = 5,
    users_per_node_variance: float = 2.5,
    main_seed=None,
    settle_time=120


class SimulationEnvironment:
    rpc_channels: List[object]


def _run_with_channels(self, config: SimulationConfig, rpc_channels):
    pass


def run(self, config: SimulationConfig):
    rpc_channels = []
    exception = None
    try:
        for addr in config.rpc_addrs:
            c = grpc.insecure_channel(addr)
            rpc_channels.append(c)
        _run_with_channels(rpc_channels)
    finally:
        for c in rpc_channels:
            try:
                c.close()
            except Exception as e:
                logging.exception('Exception while closing a channel', e)

    while True:
        self.simulate_vault_transfers()
        asyncio.sleep(self.settle_time)
        self.wait_for_equal_balances()


class Simulation:

    def __init__(
        self,
        rpc_addrs: List[str],
        initial_user_balance: int = 100000,
        users_per_node_mean: float = 5,
        users_per_node_variance: float = 2.5,
        main_seed=None,
        settle_time=(2 * 60)
    ):
        self.rpc_addrs = rpc_addrs
        self.settle_time = settle_time
        self._rand = random.Random(main_seed)

        self.node_deputies = []
        self.users = []
        for rpc_addr in self.rpc_addrs:
            self.node_deputies.append(self._rand_key())
            user_count = self._rand_normal_ordinal(
                users_per_node_mean, users_per_node_variance
            )
            for _ in range(0, user_count):
                self.node_users.append(self._rand_key())

        self._change_cond = asyncio.Condition()

    def open(self):
        pass

    def close(self):
        last_ex = None
        for c in self.rpc_channels:
            try:
                c.close()
            except Exception as e:
                last_ex = e
        if last_ex:
            raise last_ex

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _rand_child_seed(self):
        return self._rand.randrange(1 << 32)

    def _rand_normal_ordinal(self, mean, variance):
        return max(0, int(self._rand.gauss(mean, variance)))

    def _rand_user(self, client: RClient) -> User:
        key = PrivateKey.from_seed(self._rand_child_seed())
        return User(client, key)

    def wait_for_change(self):
        self._change_cond


if __name__ == '__main__':
    simul = Simulation(['172.27.0.2:40401'])
    asyncio.run(simul.run())
