import random
import asyncio
import logging
from typing import List, Optional
from dataclasses import dataclass

from rchain.client import RClient
from rchain.crypto import PrivateKey
from rchain.vault import VaultAPI


@dataclass
class VaultUserIdentity:
    name: str
    key: PrivateKey


class VaultUser:

    def __init__(
            self,
            client: RClient,
            ident: VaultUserIdentity,
            all_user_addrs: List[str],
            max_transfer_amount: int = 1000,
            max_transfer_batch_size: int = 3,
            max_sleep_time: int = 120,
            seed: Optional[int] = None):
        self.client = client
        self.ident = ident
        self.all_user_addrs = all_user_addrs
        self.max_transfer_amount = max_transfer_amount
        self.max_transfer_batch_size = max_transfer_batch_size
        self.max_sleep_time = max_sleep_time
        self.network_balance = 0
        self.local_balance = 100000
        self.transfer_lock = asyncio.Lock()
        self._logger = logging.getLogger(
            self.__class__.__name__ + '.' + self.ident.name)
        self._random = random.Random(seed)

    def set_network_balance(self, bal: int):
        self.network_balance = bal

    async def make_transfers(self):
        while self.local_balance > 0:
            transfer_count = self._random.randint(
                1, self.max_transfer_batch_size)
            self._logger.info(
                'Initial expected balance: %d REV', self.local_balance)
            self._logger.info('Deploying %d random transfers', transfer_count)
            for _ in range(0, transfer_count):
                await self._make_random_transfer()
            self._logger.info(
                'Final expected balance: %d REV', self.local_balance)
            sleep_time = self._random.randint(0, self.max_sleep_time)
            self._logger.info('Sleeping for %d seconds', sleep_time)
            await asyncio.sleep(self.max_sleep_time)

    async def _make_random_transfer(self):
        recipient = self._random.choice(self.all_user_addrs)
        amount = self._random.randint(
            1, min(self.local_balance, self.max_transfer_amount))
        await self._make_transfer(recipient, amount)

    async def _make_transfer(self, recipient, amount):
        self._logger.info(
            'Deploying transfer of %d REV to %s', amount, recipient)
        vault_api = VaultAPI(self.client, self.ident.key)
        async with self.transfer_lock:
            await asyncio.get_running_loop().run_in_executor(
                None, lambda: vault_api.deploy_transfer(
                    None, recipient, amount))
            self.local_balance -= amount
            self._logger.info('Deploy finished successfully')
