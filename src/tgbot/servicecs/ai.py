import json
import logging

from aiogram import types
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_function_message_param import ChatCompletionFunctionMessageParam
from openai.types.chat.chat_completion_system_message_param import ChatCompletionSystemMessageParam
from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam
from openai.types.chat.chat_completion_assistant_message_param import FunctionCall, ChatCompletionAssistantMessageParam
from simple_settings import settings

from tgbot import price
from tgbot.clients import http_yandex_search
from tgbot.repositories import bash, http_openai, http_text_browser, sql_chat_messages
from tgbot.repositories.http_openai import Func
from tgbot.servicecs import wallet


logger = logging.getLogger(__name__)


class ChatState:
    def __init__(self, message: types.Message, messages: list[ChatCompletionMessageParam]) -> None:
        assert message.from_user
        self.message = message
        self.user_id = message.from_user.id
        self.chat_id = message.chat.id
        self.messages = messages

    async def send(self, text: str) -> bytes | str:
        new_message = ChatCompletionUserMessageParam(role='user', content=text)
        self.messages.append(new_message)
        try:
            for _ in range(100):
                answer = await self._send_messages()
                if answer is not None:
                    return answer
        except BadCallException as e:
            self.messages.append(ChatCompletionFunctionMessageParam(
                role='function',
                name=e.func_name,
                content=e.message,
            ))
            await sql_chat_messages.create(self.user_id, self.chat_id, self.messages[-1])
        except Exception as e:
            logger.exception(e)
            self.messages.append(ChatCompletionSystemMessageParam(
                role='system',
                content='неизвестная ошибка',
            ))
            await sql_chat_messages.create(self.user_id, self.chat_id, self.messages[-1])
        return 'ошибка, попробуйте другой запрос'

    async def _send_messages(self) -> bytes | str | None:
        messages = [ChatCompletionSystemMessageParam(
            role='system',
            content=(
                'Доступная разметка текста: '
                r'**bold**, *italic*, `code`, ~~strike~~, ```c++\ncode```.'
                'Если нужен отдельно спец-символ из разметки, то экранируй его обратным слешем.'
            ),
        )] + self.messages.copy()
        resp = await http_openai.send(str(self.chat_id), messages)
        await wallet.spend(self.user_id, price.chatgpt_completion(resp.usage))
        assistant_message = ChatCompletionAssistantMessageParam(
            role=resp.choices[0].message.role,
            content=resp.choices[0].message.content,
        )
        if resp.choices[0].message.function_call:
            assistant_message['function_call'] = FunctionCall(
                name=resp.choices[0].message.function_call.name,
                arguments=resp.choices[0].message.function_call.arguments,
            )

        await sql_chat_messages.create(self.user_id, self.chat_id, self.messages[-1])
        self.messages.append(assistant_message)
        await sql_chat_messages.create(self.user_id, self.chat_id, self.messages[-1])

        function_call = assistant_message.get('function_call')
        if not function_call:
            answer = assistant_message.get('content') or ''
            return answer

        match function_call['name']:
            case Func.bash:
                raw_args = function_call['arguments']
                function_args = json.loads(raw_args)
                command = function_args.get('command')
                if not command:
                    raise ArgRequired('bash', 'command')
                await self.message.answer('исполняю команду bash..\n```{}```'.format(command))
                stdout = await bash.execute(command)
                self.messages.append(ChatCompletionFunctionMessageParam(
                    role='function',
                    name=function_call['name'],
                    content=stdout,
                ))
                return None
            case Func.web_search:
                raw_args = function_call['arguments']
                function_args = json.loads(raw_args)
                quary = function_args.get('quary')
                if not quary:
                    raise ArgRequired('web_search', 'quary')
                await self.message.answer('ищу в интернете..\n{}'.format(quary))
                content = await http_yandex_search.search(quary)
                self.messages.append(ChatCompletionFunctionMessageParam(
                    role='function',
                    name=function_call['name'],
                    content=content,
                ))
                return None
            case Func.web_read:
                raw_args = function_call['arguments']
                function_args = json.loads(raw_args)
                url = function_args.get('url')
                if not url:
                    raise ArgRequired('web_read', 'url')
                await self.message.answer('открываю `{}`'.format(url))
                content = await http_text_browser.read(url)
                self.messages.append(ChatCompletionFunctionMessageParam(
                    role='function',
                    name=function_call['name'],
                    content=content,
                ))
                return None
            case Func.create_image:
                raw_args = function_call['arguments']
                function_args = json.loads(raw_args)
                description = function_args.get('description')
                if not description:
                    raise ArgRequired('create_image', 'description')
                size = function_args.get('size')
                if not size:
                    raise ArgRequired('create_image', 'size')
                _, data = await http_openai.generate_image(description, size)
                await wallet.spend(self.user_id, price.generate_image(size))
                self.messages.append(ChatCompletionFunctionMessageParam(
                    role='function',
                    name=function_call['name'],
                    content='done',
                ))
                return data
            case _:
                raise FuncUnknow(function_call['name'])


async def get_chat_state(message: types.Message) -> ChatState:
    messages = await sql_chat_messages.get_last(
        message.chat.id,
        settings.CHAT_MESSAGES_LIMIT,
    )
    return ChatState(message, messages)


class BadCallException(Exception):
    func_name: str
    message: str


class ArgRequired(BadCallException):
    def __init__(self, func_name: str, arg_name: str) -> None:
        self.func_name = func_name
        self.message = f'argument {arg_name} required'


class FuncUnknow(BadCallException):
    def __init__(self, func_name: str) -> None:
        self.func_name = func_name
        self.message = f'unknown function name {func_name}'
