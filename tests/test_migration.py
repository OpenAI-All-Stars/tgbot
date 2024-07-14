
import subprocess


async def test_success(settings, db, db_clean):
    result = subprocess.run(['tgbot', 'migrate'])

    assert result.returncode == 0
    tables = await db.fetch(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
        """
    )
    assert [t['table_name'] for t in tables] == [
        'chat_messages',
        'schema_migrations',
        'users',
        'wallets',
        'wallets_history',
    ]
