FROM ubuntu:24.04 AS builder-image

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install --no-install-recommends -y python3 pipx && apt clean && rm -rf /var/lib/apt/lists/*

RUN pipx install poetry
ENV PATH="${PATH}:/root/.local/bin"

RUN mkdir /app
COPY . /app
WORKDIR /app

RUN ln -s /usr/bin/python3 /usr/bin/python
RUN poetry install

RUN mkdir /data
ENV DATA_PATH=/data
RUN mkdir /games
ENV GAMES_PATH=/games
RUN mkdir /prompts
ENV PROMPTS_PATH=/prompts

ENTRYPOINT [ "poetry", "run", "python", "main.py", "env" ]
