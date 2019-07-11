import random
import asyncio
import logging
from typing import List, Optional
from dataclasses import dataclass

from rchain.client import RClient
from rchain.crypto import PrivateKey
from rchain.vault import VaultAPI

from .util import randseed


@dataclass
class VaultUserConfig:
    max_amount_per_transfer: int = 1000
    max_transfer_batch_size: int = 3
    max_sleep_time: int = 120
    initial_balance: int = 0


class VaultUser:

    def __init__(
            self,
            name: str,
            client: RClient,
            all_vault_addrs: List[str],
            config: VaultUserConfig = VaultUserConfig(),
            seed: Optional[int] = None):
        self.client = client
        self.name = name
        self.all_vault_addrs = all_vault_addrs
        self.config = config
        self._random = random.Random(seed)
        key_seed = randseed(self._random)
        self.key = PrivateKey.from_seed(randseed(self._random))
        self.network_balance = 0
        self.local_balance = 0
        self.transfer_lock = asyncio.Lock()
        self._logger = logging.getLogger(
            self.__class__.__name__ + '.' + self.name)

    def set_balance(self, bal: int):
        self.network_balance = bal
        self.local_balance = bal

    async def make_transfers(self):
        while self.local_balance > 0:
            transfer_count = self._random.randint(
                1, self.config.max_transfer_batch_size)
            self._logger.info('Local balance: %d REV', self.local_balance)
            self._logger.info('Deploying %d random transfers', transfer_count)
            transfers_done = 0
            while self.local_balance > 0 and transfers_done < transfer_count:
                await self._make_random_transfer()
                transfers_done += 1
            self._logger.info('Local balance: %d REV', self.local_balance)
            sleep_time = self._random.randint(0, self.config.max_sleep_time)
            self._logger.info('Sleeping for %d seconds', sleep_time)
            await asyncio.sleep(sleep_time)

    async def _make_random_transfer(self):
        recipient = self._random.choice(self.all_vault_addrs)
        amount = self._random.randint(
            1, min(self.local_balance, self.config.max_amount_per_transfer))
        await self._make_transfer(recipient, amount)

    async def _make_transfer(self, recipient, amount):
        self._logger.info(
            'Deploying transfer of %d REV to %s', amount, recipient)
        vault_api = VaultAPI(self.client, self.key)
        async with self.transfer_lock:
            await asyncio.get_running_loop().run_in_executor(
                None, lambda: vault_api.deploy_transfer(
                    None, recipient, amount))
            self.local_balance -= amount
            self._logger.info('Deploy finished successfully')
