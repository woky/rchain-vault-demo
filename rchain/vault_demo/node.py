import asyncio
from dataclasses import dataclass
from random import Random
from typing import TYPE_CHECKING, List

import grpc
from rchain.client import RClient, RClientException
from structlog.stdlib import BoundLogger as Logger

from .common import AsyncRClient, Transfer, VaultDemoException
from .user import User


@dataclass
class NodeError(VaultDemoException):
    node: 'Node'


class NodeProposeError(NodeError):
    pass


class NodeProposeTimeoutError(NodeProposeError):
    pass


class Node:

    def __init__(self, config: dict, parent_logger: Logger):
        self.config = config
        self.rng = Random(self.config['rng_seed'])
        self.logger = parent_logger.bind(rpc_addr=self.config['address'])
        self.users = [
            User(user_config, self, self.logger)
            for user_config in self.config['users']
        ]
        self.channel = grpc.insecure_channel(self.config['address'])
        self.client = AsyncRClient(RClient(self.channel))

    def close(self):
        try:
            self.channel.close()
        except Exception:
            self.logger.error('Error while closing gRPC channel', exc_info=True)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    async def generate_transfers(self, recipients: List[str]):
        evt_loop = asyncio.get_running_loop()
        end_time = evt_loop.time() + run_duration
        propose_time_left = 0

        while evt_loop.time() < end_time:
            deploys_delay = self.rng.randint(
                self.config['deploys_min_delay'],
                self.config['deploys_max_delay'])
            propose_delay = self.rng.randint(
                self.config['propose_min_delay'],
                self.config['propose_max_delay'])

            sleep_time = propose_time_left + deploys_delay
            self.logger.info('Sleeping for %.2f seconds', sleep_time)
            await asyncio.sleep(sleep_time)
            deploys_start_time = evt_loop.time()

            self.logger.info('Starting user deploys')
            deploy_tasks = [
                asyncio.create_task(user.deploy_random_transfers(recipients))
                for user in self.users
            ]
            (done, pending) = await asyncio.wait(
                deploy_tasks, return_when=asyncio.FIRST_EXCEPTION)
            try:
                finished_transfers = [tf for t in done for tf in t.result()]
            except e:
                for t in pending:
                    t.cancel()
                raise e

            deploys_end_time = evt_loop.time()
            deploys_time_left = (
                self.config['deploys_fixed_duration'] -
                (deploys_end_time - deploys_start_time))

            sleep_time = deploys_time_left + propose_delay
            self.logger.info('Sleeping for %.2f seconds', sleep_time)
            await asyncio.sleep(sleep_time)
            propose_start_time = evt_loop.time()

            self.logger.info('Proposing')
            try:
                await asyncio.wait_for(
                    self.client.propose(), self.config['propose_time_limit'])
            except asyncio.TimeoutError:
                raise NodeProposeTimeoutError(self) from None
            except (IOError, grpc.RpcError, RClientException) as e:
                raise NodeProposeError(self)

            propose_end_time = evt_loop.time()
            propose_time_left = (
                self.config['propose_fixed_duration'] -
                (propose_start_time - propose_end_time))
