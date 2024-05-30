import logging

import click
import sentry_sdk
from simple_settings import settings

from tgbot import deps, tg_server
from tgbot.repositories import invite, sql_init

from tgbot.utils import async_command


@click.group()
def cli() -> None:
    logging.basicConfig(level=logging.INFO)
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            # Set traces_sample_rate to 1.0 to capture 100%
            # of transactions for performance monitoring.
            traces_sample_rate=1.0,
            # Set profiles_sample_rate to 1.0 to profile 100%
            # of sampled transactions.
            # We recommend adjusting this value in production.
            profiles_sample_rate=1.0,
        )


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


@cli.command()
@async_command
async def generate_invite_code() -> None:
    code = invite.generate_code()
    print(code)
