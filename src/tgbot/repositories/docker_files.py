_files = {}


def save(user_id: int, files: dict):
    _files[user_id] = files


def load(user_id: int) -> dict:
    return _files.get(user_id, {})
