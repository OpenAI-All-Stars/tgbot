import logging

import click

from tgbot import deps, tg_server
from tgbot.repositories import docker, invite, sql_init
from tgbot.servicecs import migrations

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
async def migrate() -> None:
    async with deps.use_db():
        await migrations.applay()


@cli.command()
@async_command
async def server() -> None:
    async with deps.use_all():
        await tg_server.run()


@cli.command()
@async_command
async def generate_invite_code() -> None:
    code = invite.generate_code()
    print(code)


@cli.command()
@async_command
async def pre_run() -> None:
    await docker.build()
