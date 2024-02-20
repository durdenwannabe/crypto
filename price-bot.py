# -*- coding: utf-8 -*-

import aiohttp
import asyncio
import argparse
import datetime
import discord
import logging
import os
import requests
import toml

from pyserum.async_connection import async_conn
from pyserum.market import AsyncMarket
from solana.rpc.async_api import AsyncClient
from dataclasses import dataclass


@dataclass
class MarketData:
    timestamp: datetime.datetime
    last: float


client = discord.Client()

# noinspection PyTypeChecker
argument_parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                          description="Serum-based price BOT")

argument_parser.add_argument('-c', '--config-file', help="configuration file name", default='xLFNTY.toml')
args = argument_parser.parse_args()

config_path = args.config_file if args.config_file else os.path.abspath(__file__).replace('.py', '.toml')
config = toml.load(config_path)

symbol = config['Symbol']
digits = config['Digits']
suffix = config['Suffix']
currency = config['Currency']
rpc = config['Rpc']

if 'RpcRedirect' in config:
    response = requests.get(config['RpcRedirect'])
    rpc = response.text

# noinspection SpellCheckingInspection
logging.basicConfig(format='%(asctime)s.%(msecs)03d,%(levelname)s,%(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)
logger = logging.getLogger(__name__)

# markets = {}
market_data = None
fmt_str = f'{{:.{digits}f}}'


async def update_bot_status():
    global market_data
    try:
        while True:
            try:
                async with async_conn(rpc) as cc:
                    market = await AsyncMarket.load(cc, '7vLJCTpXcF4Tr4Nt42PyPQCcQud3MMQ6cuYd9bqzfxbQ')
                    while True:
                        asks = await market.load_asks()
                        # print(f"asks load {asks}")
                        bids = await market.load_bids()
                        # print(f"bids load {bids}")

                        l2_asks = asks.get_l2(1)
                        l2_bids = bids.get_l2(1)

                        if len(l2_asks) > 0 and len(l2_bids) > 0:
                            # print('ask', l2_asks[0].price, 'bid', l2_bids[0].price)

                            middle = (l2_asks[0].price + l2_bids[0].price) / 2
                            # print(f'middle {middle}')

                            last = middle
                            last_str = f'x: ${fmt_str.format(l2_bids[0].price)}-${fmt_str.format(l2_asks[0].price)}'
                            # nickname = f"{suffix}{last_str} {m['quoteCurrency']}"
                            nickname = f"{last_str}"
                            for g in client.guilds:
                                await client.get_guild(g.id).me.edit(nick=nickname)
                                await asyncio.sleep(0.5)
                            if market_data is not None:
                                start = market_data.last
                                change = (last - start) / last * 100
                                # print(last, start, change)
                                status = f"{currency} | {change:+.2f} %"
                                await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status))

                            now = datetime.datetime.utcnow()
                            if market_data is None or now.date() > market_data.timestamp.date():
                                market_data = MarketData(now, last)
                                # print(now, last, start, change)

                        await asyncio.sleep(10.0)
            except Exception as e:
                # logger.error(e)
                pass

            await asyncio.sleep(5)
    except asyncio.CancelledError:
        raise


@client.event
async def on_ready():
    # for channel in client.get_all_channels():
    #     if channel.name == "general":
    #         # TODO: 発言するチャンネルをここで探索したりする
    #         pass
    #     # print(channel.name)
    # print(client.guilds)
    asyncio.create_task(update_bot_status())


@client.event
async def on_message(message):
    # noinspection PyBroadException
    try:
        pass
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.error("error in on_message", exc_info=True)


def main():
    client.run(config['DiscordToken'])


if __name__ == '__main__':
    try:
        import platform
        if platform.system() != 'Windows':
            # noinspection PyUnresolvedReferences
            import uvloop
            uvloop.install()
        main()
    except KeyboardInterrupt:
        pass
