import asyncio
import sys
import contextlib
import json
import logging
from pathlib import Path
from random import Random
from typing import List

import structlog
from rchain.crypto import PrivateKey
from rchain.util import load_contract

from .node import Node
from .user import User
from .common import AsyncRClient


class World:

    logger = structlog.get_logger()

    def __init__(self, config: dict):
        self.config = config
        self.rng = Random(self.config['rng_seed'])
        self.admin_key = PrivateKey.from_hex(self.config['admin_key'])
        self.admin_rev_addr = self.admin_key.get_public_key().get_address()

    async def _init_vaults(self, client: AsyncRClient, users: List[User]):
        # account for possible deploy fees for transfers from genesis vault by
        # 1.2 factor
        balance = int(1.2 * sum(u.config['initial_balance'] for u in users))
        self.logger.info(
            'Initializing genesis vault %s with balance of %d REV',
            self.admin_rev_addr, balance)
        await client.deploy(
            self.admin_key,
            contract=load_contract(
                'rchain.vault', 'create_genesis_vault.rho.tpl', {
                    'addr': self.admin_rev_addr,
                    'balance': balance
                }))
        await client.propose()

        for u in users:
            self.logger.info(
                'Transferring %d REV to vault %s', u.config['initial_balance'],
                u.rev_addr)
            await client.deploy(
                self.admin_key,
                contract=load_contract(
                    'rchain.vault', 'transfer.rho.tpl', {
                        'from': self.admin_rev_addr,
                        'to': u.rev_addr,
                        'amount': u.config['initial_balance']
                    }))
        await client.propose()

    async def _get_user_balances(self, client: AsyncRClient, users: List[User]):
        deploy_ids = [
            await client.deploy(
                self.admin_key,
                contract=load_contract(
                    'rchain.vault', 'get_balance.rho.tpl',
                    {'addr': u.rev_addr})) for u in users
        ]
        await client.propose()
        balances = []
        for deploy_id in deploy_ids:
            data = await client.get_data_at_deploy_id(deploy_id)
            bal = data.blockResults[0].postBlockData[0].exprs[0].g_int
            balances.append(bal)

    async def main(self):
        with contextlib.ExitStack() as stack:
            nodes = [
                stack.enter_context(Node(node_config, self.logger))
                for node_config in config['nodes']
            ]
            users = [u for n in nodes for u in n.users]
            client = nodes[0].client
            await self._init_vaults(client, users)

            recipients = [u.rev_addr for u in users]
            tasks = [n.generate_transfers(recipients, 120) for n in nodes]
            (done, pending) = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_EXCEPTION)
            for t in done:
                t.result()

            balances = await self._get_user_balances(client, users)
            for u, bal in zip(users, balances):
                self.logger.info('User %s expected balance: %d', u.balance)
                self.logger.info('User %s actual balance:   %d', bal)

if __name__ == '__main__':

    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.stdlib.PositionalArgumentsFormatter(),
    ]

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(),
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    config = json.loads(Path('config.json').read_text())
    w = World(config)
    asyncio.run(w.main())
