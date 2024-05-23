from enum import Enum
import openai
from openai.openai_object import OpenAIObject
from simple_settings import settings


class Func(str, Enum):
    bash = 'bash'
    web_search = 'web_search'
    web_read = 'web_read'


FUNCTIONS = [
    {
        'name': Func.bash,
        'description': 'Execute any bash command in Debian buster, see output, store session',
        'parameters': {
            'type': 'object',
            'properties': {
                'command': {
                    'type': 'string',
                    'description': 'Bash command body',
                },
            },
            'required': ['command'],
        },
    },
    {
        'name': Func.web_search,
        'description': 'Search on internet',
        'parameters': {
            'type': 'object',
            'properties': {
                'quary': {
                    'type': 'string',
                    'description': 'Search quary',
                },
            },
            'required': ['quary'],
        },
    },
    {
        'name': Func.web_read,
        'description': 'Open url and read it, return text as markdown',
        'parameters': {
            'type': 'object',
            'properties': {
                'url': {
                    'type': 'string',
                    'description': 'url',
                },
            },
            'required': ['url'],
        },
    },
]


async def send(user: str, messages: list[dict]) -> OpenAIObject:
    return await openai.ChatCompletion.acreate(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        messages=messages,
        functions=FUNCTIONS,
        function_call='auto',
        user=user,
    )
