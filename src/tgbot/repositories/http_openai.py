import openai
from openai.openai_object import OpenAIObject
from simple_settings import settings


FUNCTIONS = [
    {
        'name': 'execute_bash',
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
