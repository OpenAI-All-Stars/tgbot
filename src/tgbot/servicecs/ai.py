import json
import logging

from aiogram import types

from tgbot.clients import http_yandex_search
from tgbot.entities.user import User
from tgbot.repositories import bash, http_openai, sql_chat_messages
from tgbot.repositories.http_openai import Func


logger = logging.getLogger(__name__)


class ChatState:
    def __init__(self, message: types.Message, user: User, messages: list[dict]) -> None:
        self.message = message
        self.user = user
        self.messages = messages

    async def send(self) -> str:
        new_message = {'role': 'user', 'content': self.message.text}
        self.messages.append(new_message)
        try:
            return await self._send_messages()
        except BadCallException as e:
            self.messages.append({
                'role': 'function',
                'content': e.message,
            })
        except Exception as e:
            logger.error(e)
        return 'ошибка, попробуйте другой запрос'

    async def _send_messages(self) -> str:
        resp = await http_openai.send(str(self.user.chat_id), self.messages)
        response_message = resp.choices[0].message

        await sql_chat_messages.create(self.user.chat_id, self.messages[-1])

        function_call = response_message.get('function_call')
        if not function_call:
            answer = response_message.content
            await sql_chat_messages.create(self.user.chat_id, dict(response_message))
            return answer
        self.messages.append({
            'role': 'function',
            'name': function_call['name'],
            'content': response_message,
        })
        match function_call['name']:
            case Func.bash:
                await self.message.answer('исполняю команду bash..')
                raw_args = function_call['arguments']
                function_args = json.loads(raw_args)
                command = function_args.get('command')
                if not command:
                    raise ArgRequired('command')
                stdout = await bash.execute(command)
                self.messages.append({
                    'role': 'function',
                    'name': function_call['name'],
                    'content': stdout,
                })
                return await self._send_messages()
            case Func.web_search:
                await self.message.answer('ищу в интернете..')
                raw_args = function_call['arguments']
                function_args = json.loads(raw_args)
                quary = function_args.get('quary')
                if not quary:
                    raise ArgRequired('quary')
                content = await http_yandex_search.search(quary)
                await sql_chat_messages.create(self.user.chat_id, dict(response_message))
                self.messages.append({
                    'role': 'function',
                    'name': function_call['name'],
                    'content': content,
                })
                # TODO: потенциально бесконечная рекурсия
                return await self._send_messages()
            case _:
                raise FuncUnknow(function_call['name'])


async def get_chat_state(message: types.Message, user: User) -> ChatState:
    messages = await sql_chat_messages.get_last(user.chat_id, 10)
    return ChatState(message, user, messages)


class BadCallException(Exception):
    message: str


class ArgRequired(BadCallException):
    def __init__(self, arg_name: str) -> None:
        self.message = f'argument {arg_name} required'


class FuncUnknow(BadCallException):
    def __init__(self, func_name: str) -> None:
        self.message = f'unknown function name {func_name}'
