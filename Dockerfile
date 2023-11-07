FROM python:3.11-buster

ENV SIMPLE_SETTINGS tgbot.settings.prod

WORKDIR /app/

ENV POETRY_VIRTUALENVS_CREATE false
RUN pip install poetry

COPY . .

RUN poetry install --no-dev

CMD ["sh", "-c", "tgbot server"]
