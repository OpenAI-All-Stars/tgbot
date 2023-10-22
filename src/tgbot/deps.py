from aiosqlite import Connection

from tgbot.registry import RegistryValue


db = RegistryValue[Connection]()
