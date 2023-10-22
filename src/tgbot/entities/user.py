from dataclasses import dataclass


@dataclass
class User:
    user_id: int
    chat_id: int
    full_name: str
    username: str
