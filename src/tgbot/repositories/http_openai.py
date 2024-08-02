import asyncio
from enum import Enum
import io

import httpx
from openai.types.chat.chat_completion import ChatCompletion
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.completion_create_params import Function
from PIL import Image
from simple_settings import settings

from tgbot.deps import openai_client
from tgbot.types import ImageSizeType


class Func(str, Enum):
    bash = 'bash'
    web_search = 'web_search'
    web_read = 'web_read'
    create_image = 'create_image'
    python = 'python'
    python_files = 'python_files'


FUNCTIONS = [
    # Function(
    #     name=Func.bash,
    #     description='Execute any bash command in Debian buster, see output, store session',
    #     parameters={
    #         'type': 'object',
    #         'properties': {
    #             'command': {
    #                 'type': 'string',
    #                 'description': 'Bash command body',
    #             },
    #         },
    #         'required': ['command'],
    #     },
    # ),
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
                'size': {
                    'type': 'string',
                    'description': 'Image size',
                    'enum': ['1024x1024', '1792x1024', '1024x1792']
                },
            },
            'required': ['description', 'size'],
        },
    ),
    Function(
        name=Func.python,
        description=(
            'Execute python code in docker. Returns log. '
            'Create files only in the current folder.'
        ),
        parameters={},
    ),
    Function(
        name=Func.python_files,
        description='Send files to user created by python code running previous time.',
        parameters={
            'type': 'object',
            'properties': {
                'filenames': {
                    'type': 'array',
                    'description': 'List of file names in app root',
                    'items': {
                        'type': 'string'
                    }
                },
            },
            'required': ['filenames'],
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


async def generate_image(promt: str, size: ImageSizeType) -> tuple[str, bytes]:
    client = openai_client.get()
    response = await client.images.generate(
        model='dall-e-3',
        prompt=promt,
        size=size,
        quality='standard',
        n=1,
    )
    url = response.data[0].url
    assert url
    data = await asyncio.get_running_loop().run_in_executor(None, _resize, url)
    return url, data.getvalue()


async def audio2text(audio_file: io.BytesIO) -> str:
    client = openai_client.get()
    transcription = await client.audio.transcriptions.create(
        file=audio_file,
        model='whisper-1',
    )
    return transcription.text


def _resize(url: str) -> io.BytesIO:
    r = httpx.get(url)
    r.raise_for_status()
    image = Image.open(io.BytesIO(r.content))
    image.thumbnail((1024, 1024))
    byte_arr = io.BytesIO()
    image.save(byte_arr, format='JPEG')
    return byte_arr
