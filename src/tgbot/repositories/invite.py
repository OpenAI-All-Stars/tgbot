import json
import time

import jwt
from simple_settings import settings


FIRST_SEGMENT = json.dumps({
  "alg": "HS256",
  "typ": "JWT",
})


def generate_code():
    encoded_jwt = jwt.encode(time.time(), settings.SECRET_INVITE, algorithm='HS256')
    parts = encoded_jwt.split('.')
    return '.'.join(parts[1:])


def get_payload(code: str) -> str | None:
    try:
        payload = jwt.decode(f'{FIRST_SEGMENT}.{code}', settings.SECRET_INVITE, algorithms=['HS256'])
    except jwt.PyJWTError:
        return None
    return str(payload)
