FROM python:3.12-bullseye

ENV SIMPLE_SETTINGS tgbot.settings.prod

WORKDIR /app/

ENV POETRY_VIRTUALENVS_CREATE false
RUN pip install poetry

COPY poetry.lock .
COPY pyproject.toml .

RUN poetry install --only-root

COPY . .

RUN poetry install --no-dev

CMD ["sh", "-c", "tgbot server"]
