import os
from pathlib import Path

from tgbot.repositories import sql_schema_migrations


async def applay():
    applied_migrations = await sql_schema_migrations.get_applied_migrations()
    migrations_path = Path(__file__).parent.parent.parent.parent / 'contrib' / 'migrations'
    migration_files = sorted(f for f in os.listdir(migrations_path) if f.endswith('.sql'))
    for migration_file in migration_files:
        version = migration_file.split('_')[0]
        if version not in applied_migrations:
            with open(migrations_path / migration_file, 'r') as f:
                sql = f.read()
                await sql_schema_migrations.apply_migration(version, sql)
                print(f'Applied migration: {migration_file}')
