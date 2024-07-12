from tgbot.deps import db
from tgbot.entities.user import User


async def create(user_id: int, chat_id: int, code: str, full_name: str, username: str) -> None:
    await db.get().execute(
        """
        INSERT INTO users (user_id, chat_id, invite_code, full_name, username)
        VALUES ($1, $2, $3, $4, $5)
        """,
        user_id, chat_id, code, full_name, username,
    )


async def exists(user_id: int) -> bool:
    return await db.get().fetchval(
        """
        SELECT COUNT(*) AS cnt FROM users
        WHERE user_id = $1
        """,
        user_id,
    ) > 0


async def exists_code(code: str) -> bool:
    return await db.get().fetchval(
        """
        SELECT COUNT(*) FROM users
        WHERE invite_code = $1
        """,
        code,
    ) > 0


async def get(user_id: int) -> User | None:
    row = await db.get().fetchrow(
        """
        SELECT * FROM users
        WHERE user_id = $1
        """,
        user_id,
    )
    if not row:
        return
    return User(
        user_id=row['user_id'],
        chat_id=row['chat_id'],
        full_name=row['full_name'],
        username=row['username'],
    )
