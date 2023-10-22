import json
import time

from tgbot.deps import db


async def create(chat_id: int, body: dict) -> None:
    await db.get().execute(
        """
        INSERT INTO chat_messages (chat_id, body, created_at)
        VALUES ($1, $2, $3)
        """,
        [chat_id, json.dumps(body), int(time.time())],
    )
    await db.get().commit()


async def get_last(chat_id: int, limit: int) -> list[dict]:
    q = db.get().execute(
        """
        SELECT body, created_at FROM chat_messages
        WHERE chat_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        [chat_id, limit],
    )
    async with q as cursor:
        rows = await cursor.fetchall()
    rows = sorted(rows, key=lambda x: x['created_at'])
    return [
        json.loads(row['body'])
        for row in rows
    ]
