from pathlib import Path

import aiosqlite
import click

from tgbot import tg_server

from tgbot.utils import async_command


@click.group()
def cli() -> None:
    ...


@cli.command()
@async_command
async def create_db() -> None:
    async with aiosqlite.connect('db.sqlite3') as db:
        f_name = Path(__file__).parent.parent.parent / 'contrib' / 'sqlite.sql'
        with open(f_name) as f:
            queries = f.read().split(';')
        for q in queries:
            await db.execute(q)
            await db.commit()


@cli.command()
@async_command
async def server() -> None:
    await tg_server.run()
