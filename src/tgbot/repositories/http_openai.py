from enum import Enum
from typing import Literal

from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.completion_create_params import Function
from simple_settings import settings

from tgbot.deps import openai_client


SizeType = Literal["256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"]


class Func(str, Enum):
    bash = 'bash'
    web_search = 'web_search'
    web_read = 'web_read'
    create_image = 'create_image'


FUNCTIONS = [
    Function(
        name=Func.bash,
        description='Execute any bash command in Debian buster, see output, store session',
        parameters={
            'type': 'object',
            'properties': {
                'command': {
                    'type': 'string',
                    'description': 'Bash command body',
                },
            },
            'required': ['command'],
        },
    ),
    Function(
        name=Func.web_search,
        description='Search on internet',
        parameters={
            'type': 'object',
            'properties': {
                'quary': {
                    'type': 'string',
                    'description': 'Search quary',
                },
            },
            'required': ['quary'],
        },
    ),
    Function(
        name=Func.web_read,
        description='Open url and read it, return text as markdown',
        parameters={
            'type': 'object',
            'properties': {
                'url': {
                    'type': 'string',
                },
            },
            'required': ['url'],
        },
    ),
    Function(
        name=Func.create_image,
        description='Generate image by dall-e',
        parameters={
            'type': 'object',
            'properties': {
                'description': {
                    'type': 'string',
                    'description': 'Image promt',
                },
            },
            'required': ['description'],
        },
    ),
]


async def send(user: str, messages: list[ChatCompletionMessageParam]) -> ChatCompletion:
    client = openai_client.get()
    return await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        functions=FUNCTIONS,
        function_call='auto',
        user=user,
    )


async def generate_image(promt: str, size: SizeType | None = None) -> str | None:
    client = openai_client.get()
    response = await client.images.generate(
        model='dall-e-3',
        prompt=promt,
        size=size or '1024x1024',
        quality='standard',
        n=1,
    )
    return response.data[0].url
