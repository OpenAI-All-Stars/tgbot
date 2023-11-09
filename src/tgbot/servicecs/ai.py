import json

from tgbot.deps import duck_client
from tgbot.entities.user import User
from tgbot.repositories import bash, http_openai, sql_chat_messages
from tgbot.repositories.http_openai import Func


class ChatState:
    def __init__(self, user: User, messages: list[dict]) -> None:
        self.user = user
        self.messages = messages

    @property
    def need_approve(self) -> bool:
        return len(self.messages) > 0 and 'function_call' in self.messages[-1]

    async def execute(self) -> str:
        if not self.messages:
            return 'Нечего исполнять'
        message = self.messages[-1]
        function_call = message['function_call']
        match function_call['name']:
            case Func.bash:
                raw_args = function_call['arguments']
                function_args = json.loads(raw_args)
                command = function_args.get('command')
                if not command:
                    raise Exception('no command arg')
                stdout = await bash.execute(command)
                self.messages.append({
                    'role': 'function',
                    'name': function_call['name'],
                    'content': stdout,
                })
                return await self._send_messages()
            case _:
                raise Exception('bad func name {}'.format(function_call['name']))

    async def send(self, text: str) -> str:
        new_message = {'role': 'user', 'content': text}
        self.messages.append(new_message)
        for _ in range(3):
            try:
                return await self._send_messages()
            except BadCallException as e:
                self.messages.append({
                    'role': 'system',
                    'content': e.message,
                })
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
        match function_call['name']:
            case Func.bash:
                raw_args = function_call['arguments']
                function_args = json.loads(raw_args)
                command = function_args.get('command')
                if not command:
                    raise ArgRequired('command')
                await sql_chat_messages.create(self.user.chat_id, dict(response_message))
                return 'Разрешить исполнение?\n`{}`'.format(command)
            case Func.duckduckgo:
                raw_args = function_call['arguments']
                function_args = json.loads(raw_args)
                quary = function_args.get('quary')
                if not quary:
                    raise ArgRequired('quary')
                content = ''
                async for item in duck_client.get().text(keywords=quary, max_results=1):
                    content = json.dumps(item)
                    break
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


async def get_chat_state(user: User) -> ChatState:
    messages = await sql_chat_messages.get_last(user.chat_id, 10)
    return ChatState(user, messages)


class BadCallException(Exception):
    message: str


class ArgRequired(BadCallException):
    def __init__(self, arg_name: str) -> None:
        self.message = f'argument {arg_name} required'


class FuncUnknow(BadCallException):
    def __init__(self, func_name: str) -> None:
        self.message = f'unknown function name {func_name}'
