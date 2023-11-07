from pathlib import Path

from tgbot.deps import db


async def create_db() -> None:
    f_name = Path(__file__).parent.parent.parent.parent / 'contrib' / 'sqlite.sql'
    with open(f_name) as f:
        queries = f.read().split(';')
    for q in queries:
        await db.get().execute(q)
        await db.get().commit()
