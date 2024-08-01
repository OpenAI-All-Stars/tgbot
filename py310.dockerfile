FROM python:3.10-slim

RUN pip install numpy
RUN pip install matplotlib

WORKDIR /app
