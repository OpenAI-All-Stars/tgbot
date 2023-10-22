FROM python:3.11-buster

ENV SIMPLE_SETTINGS tgbot.settings.prod
ENV CLI_COMMAND server

WORKDIR /app/

ENV POETRY_VIRTUALENVS_CREATE false
RUN pip install poetry

COPY . .

RUN poetry install --no-dev

WORKDIR /root/

EXPOSE 8000

CMD ["sh", "-c", "tgbot server"]
