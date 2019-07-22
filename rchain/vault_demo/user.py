import asyncio
from dataclasses import dataclass
from random import Random
from typing import List

import grpc
from rchain.client import RClientException
from rchain.crypto import PrivateKey
from rchain.util import load_contract
from structlog.stdlib import BoundLogger as Logger

from .common import Transfer, VaultDemoException


@dataclass
class UserDeployError(VaultDemoException):
    user: 'User'


class UserDeployTimeoutError(UserDeployError):
    pass


class User:

    def __init__(self, config: dict, node: 'Node', parent_logger: Logger):
        self.node = node
        self.config = config
        self.rng = Random(self.config['rng_seed'])
        self.key = PrivateKey.from_hex(self.config['key'])
        self.rev_addr = self.key.get_public_key().get_address()
        self.balance = self.config['initial_balance']
        self.logger = parent_logger.bind(rev_addr=self.rev_addr)
        self.deploy_counter = 0

    async def _deploy_transfer(self, recipient: str, amount: int):
        contract = load_contract(
            'rchain.vault', 'transfer.rho.tpl', {
                'from': self.rev_addr,
                'to': recipient,
                'amount': amount
            })
        try:
            self.deploy_counter += 1
            await asyncio.wait_for(
                self.node.client.deploy(
                    self.key, contract, ts=self.deploy_counter),
                self.config['deploy_time_limit'])
            self.balance -= amount
        except asyncio.TimeoutError:
            raise UserDeployTimeoutError(self) from None
        except (IOError, grpc.RpcError, RClientException) as e:
            raise UserDeployError(self)

    async def deploy_random_transfers(self, recipients: List[str]) -> List[Transfer]:
        transfer_batch_size = self.rng.randint(
            self.config['deploy_batch_min_size'],
            self.config['deploy_batch_max_size'])
        self.logger.info('Deploying %s random transfers', transfer_batch_size)
        self.logger.info(
            'Expected balance (before transfers): %d', self.balance)
        finished_transfers = []
        for _ in range(0, transfer_batch_size):
            recipient = self.rng.choice(recipients)
            transfer_amount = min(
                self.balance,
                self.rng.randint(
                    self.config['transfer_min_amount'],
                    self.config['transfer_max_amount']))
            self.logger.info(
                'Deploying transfer of %d REV to %s', transfer_amount,
                recipient)
            await self._deploy_transfer(recipient, transfer_amount)
            finished_transfers.append(
                Transfer(self.rev_addr, recipient, transfer_amount))
        self.logger.info(
            'Expected balance (after transfers):  %d', self.balance)
        return finished_transfers
