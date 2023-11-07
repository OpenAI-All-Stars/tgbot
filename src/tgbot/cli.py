import logging

import click

from tgbot import deps, tg_server
from tgbot.repositories import sql_init

from tgbot.utils import async_command


@click.group()
def cli() -> None:
    logging.basicConfig(level=logging.INFO)


@cli.command()
@async_command
async def create_db() -> None:
    async with deps.use_db():
        await sql_init.create_db()


@cli.command()
@async_command
async def server() -> None:
    async with deps.use_all():
        await sql_init.create_db()
        await tg_server.run()
