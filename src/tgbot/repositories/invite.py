import time

import jwt
from simple_settings import settings


ALG = 'HS256'
FIRST_SEGMENT = jwt.encode(
    {},
    settings.SECRET_INVITE,
    algorithm=ALG,
).split('.')[0]


def generate_code():
    encoded_jwt = jwt.encode({'t': time.time()}, settings.SECRET_INVITE, algorithm=ALG)
    parts = encoded_jwt.split('.')
    return '.'.join(parts[1:])


def get_payload(code: str) -> str | None:
    try:
        payload = jwt.decode(f'{FIRST_SEGMENT}.{code}', settings.SECRET_INVITE, algorithms=[ALG])
    except jwt.PyJWTError:
        return None
    return str(payload['t'])
