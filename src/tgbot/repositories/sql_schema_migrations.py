from tgbot.deps import db


async def get_applied_migrations() -> set[str]:
    await db.get().execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(255) PRIMARY KEY
        );
    """)
    rows = await db.get().fetch("SELECT version FROM schema_migrations")
    return {row['version'] for row in rows}


async def apply_migration(version: str, sql: str):
    async with db.get().acquire() as con:
        async with con.transaction():
            await con.execute(sql)
            await con.execute("INSERT INTO schema_migrations (version) VALUES (%s)", version)
