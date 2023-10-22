import json

from tgbot.entities.user import User
from tgbot.repositories import bash, http_openai, sql_chat_messages


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
            case 'execute_bash':
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
        return await self._send_messages()

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
            case 'execute_bash':
                raw_args = function_call['arguments']
                function_args = json.loads(raw_args)
                command = function_args.get('command')
                if not command:
                    raise Exception('no command arg')
                await sql_chat_messages.create(self.user.chat_id, dict(response_message))
                return 'Разрешить исполнение?\n{}'.format(repr(command))
            case _:
                raise Exception('bad func name {}'.format(function_call['name']))


async def get_chat_state(user: User) -> ChatState:
    messages = await sql_chat_messages.get_last(user.chat_id, 10)
    return ChatState(user, messages)
