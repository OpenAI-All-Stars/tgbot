from datetime import datetime, timedelta
import logging

from simple_settings import settings

from tgbot.deps import db
from tgbot.repositories import sql_chat_messages
from tgbot.utils import worker


logger = logging.getLogger(__name__)
CLEAN_INTERVAL_S = 60


@worker(timeout_s=CLEAN_INTERVAL_S)
async def clean_chat_messages_worker():
    active_chats = await sql_chat_messages.get_active_chats(
        datetime.now() - timedelta(seconds=CLEAN_INTERVAL_S * 2)
    )
    for chat_id in active_chats:
        try:
            async with db.get().transaction():
                first_created_at = await sql_chat_messages.get_first_date_of_last(
                    chat_id,
                    settings.CHAT_MESSAGES_LIMIT,
                )
                await sql_chat_messages.delete_old_at(chat_id, first_created_at)
        except Exception as e:
            logger.exception(e)
