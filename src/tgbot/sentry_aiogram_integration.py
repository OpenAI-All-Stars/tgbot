import contextvars
from typing import Any, Awaitable, Callable
from uuid import uuid4

from aiogram import BaseMiddleware, Dispatcher, types
import sentry_sdk
from simple_settings import settings


_CRUMB_MARKER = 'aiogram_current_handler_id'
_current_handler_id = contextvars.ContextVar('current_handler_id')


def init(dp: Dispatcher):
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
            before_breadcrumb=modify_breadcrumb,
            before_send=filter_event,
        )
        dp.update.outer_middleware.register(AiogramMiddleware())


class AiogramMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        token = _current_handler_id.set(str(uuid4()))
        try:
            return await handler(event, data)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            raise
        finally:
            _current_handler_id.reset(token)


def modify_breadcrumb(breadcrumb, hint):
    hid = _current_handler_id.get(None)
    if hid:
        breadcrumb[_CRUMB_MARKER] = hid
    return breadcrumb


def filter_event(event, hint):
    if 'breadcrumbs' in event:
        hid = _current_handler_id.get(None)
        if hid:
            event['breadcrumbs']['values'] = [
                crumb for crumb in event['breadcrumbs']['values']
                if crumb.get(_CRUMB_MARKER) == hid
            ]
    return event
