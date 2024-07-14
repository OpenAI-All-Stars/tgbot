import json

from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_function_message_param import ChatCompletionFunctionMessageParam
from openai.types.chat.chat_completion_system_message_param import ChatCompletionSystemMessageParam
from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam
from openai.types.chat.chat_completion_assistant_message_param import FunctionCall, ChatCompletionAssistantMessageParam

from tgbot.deps import db


async def create(user_id: int, chat_id: int, body: ChatCompletionMessageParam) -> None:
    await db.get().execute(
        """
        INSERT INTO chat_messages (user_id, chat_id, body)
        VALUES ($1, $2, $3)
        """,
        user_id, chat_id, json.dumps(body),
    )


async def get_last(chat_id: int, limit: int) -> list[ChatCompletionMessageParam]:
    rows = await db.get().fetch(
        """
        SELECT body, created_at FROM chat_messages
        WHERE chat_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        chat_id, limit,
    )
    return [
        convert2type(json.loads(row['body']))
        for row in reversed(rows)
    ]


async def clean(chat_id: int) -> None:
    await db.get().execute(
        """
        DELETE FROM chat_messages WHERE chat_id = $1
        """,
        chat_id,
    )


def convert2type(body: dict) -> ChatCompletionMessageParam:
    match body['role']:
        case 'system':
            return ChatCompletionSystemMessageParam(
                role=body['role'],
                content=body['content'],
            )
        case 'user':
            return ChatCompletionUserMessageParam(
                role=body['role'],
                content=body['content'],
            )
        case 'assistant':
            function_call = body.get('function_call')
            param = ChatCompletionAssistantMessageParam(
                role=body['role'],
                content=body.get('content'),
            )
            if function_call:
                param['function_call'] = FunctionCall(
                    arguments=function_call['arguments'],
                    name=function_call['name'],
                )
            return param
        case 'function':
            return ChatCompletionFunctionMessageParam(
                role=body['role'],
                name=body['name'],
                content=body.get('content'),
            )
    raise Exception('bad body: {}'.format(body))
