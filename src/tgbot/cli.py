import logging
from pathlib import Path

import click

from tgbot import deps, tg_server

from tgbot.utils import async_command


@click.group()
def cli() -> None:
    logging.basicConfig(level=logging.INFO)


@cli.command()
@async_command
async def create_db() -> None:
    async with deps.use_db() as db:
        f_name = Path(__file__).parent.parent.parent / 'contrib' / 'sqlite.sql'
        with open(f_name) as f:
            queries = f.read().split(';')
        for q in queries:
            await db.execute(q)
            await db.commit()


@cli.command()
@async_command
async def server() -> None:
    async with deps.use_all():
        await tg_server.run()
