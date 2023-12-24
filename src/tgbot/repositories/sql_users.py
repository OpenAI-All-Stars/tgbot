from tgbot.deps import db
from tgbot.entities.user import User


async def create(user_id: int, chat_id: int, code: str, full_name: str, username: str) -> None:
    await db.get().execute(
        """
        INSERT INTO users (user_id, chat_id, invite_code, full_name, username)
        VALUES ($1, $2, $3, $4, $5)
        """,
        [user_id, chat_id, code, full_name, username],
    )
    await db.get().commit()


async def exists(user_id: int) -> bool:
    cursor = await db.get().execute(
        """
        SELECT COUNT(*) AS cnt FROM users
        WHERE user_id = $1
        """,
        [user_id],
    )
    row = await cursor.fetchone()
    await cursor.close()
    return row is not None and row['cnt'] > 0


async def exists_code(code: str) -> bool:
    cursor = await db.get().execute(
        """
        SELECT COUNT(*) AS cnt FROM users
        WHERE invite_code = $1
        """,
        [code],
    )
    row = await cursor.fetchone()
    await cursor.close()
    return row is not None and row['cnt'] > 0


async def get(user_id: int) -> User | None:
    cursor = await db.get().execute(
        """
        SELECT * FROM users
        WHERE user_id = $1
        """,
        [user_id],
    )
    row = await cursor.fetchone()
    if not row:
        return None
    await cursor.close()
    return User(
        user_id=row['user_id'],
        chat_id=row['chat_id'],
        full_name=row['full_name'],
        username=row['username'],
    )
