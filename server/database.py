#  Date: 18.01.2025
# 
#  Author: Amanda Uccello
#  Class: ICS4UR-1
#  School: Port Credit Secondary School
#  Teacher: Mrs. Kim
#  Description: 
#      Handle the postgres database connection and queries
#      Keeps track of the chat turns and messages


from __future__ import annotations as _annotations

import asyncio
import psycopg2
from psycopg2 import sql
from collections.abc import AsyncIterator
from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Annotated, Any, Callable, Literal, LiteralString, ParamSpec, TypeVar
import sys
import os
from fastapi import Depends, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse

from pydantic import Field, TypeAdapter
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

import logfire
from collections import deque

sys.path.append(str(Path(__file__).parent.parent))

THIS_DIR = Path(__file__).parent

MessageTypeAdapter: TypeAdapter[ModelMessage] = TypeAdapter(
    Annotated[ModelMessage, Field(discriminator='kind')]
)
P = ParamSpec('P')
R = TypeVar('R')


@dataclass
class Database:
    """Database to store chat messages in PostgreSQL.
    """

    con: psycopg2.extensions.connection
    _loop: asyncio.AbstractEventLoop
    _executor: ThreadPoolExecutor

    @classmethod
    @asynccontextmanager
    async def connect(
            cls, dbname: str, user: str, password: str, host: str, port: int
    ) -> AsyncIterator[Database]:
        with logfire.span('connect to DB'):
            loop = asyncio.get_event_loop()
            executor = ThreadPoolExecutor(max_workers=1)
            con = await loop.run_in_executor(
                executor, partial(psycopg2.connect, dbname=dbname, user=user, password=password, host=host, port=port)
            )
            slf = cls(con, loop, executor)
            try:
                yield slf
            finally:
                await slf._asyncify(con.close)

    async def _asyncify(
            self, func: Callable[..., R], *args: Any, **kwargs: Any
    ) -> R:
        return await self._loop.run_in_executor(
            self._executor,
            partial(func, *args, **kwargs),
        )

    async def create_tables(self):
        cur = await self._asyncify(self.con.cursor)
        try:
            await self._asyncify(cur.execute, "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
            await self._asyncify(cur.execute, "CREATE SEQUENCE IF NOT EXISTS message_ordinal_seq;")
            await self._asyncify(cur.execute, """
            CREATE TABLE IF NOT EXISTS turns (
                /* id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),*/
                id UUID PRIMARY KEY,
                turn_id TEXT,
                ordinal SERIAL,
                version TEXT DEFAULT '0.0.1',           
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS messages (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                turn_id UUID REFERENCES turns(id),
                message_list BYTEA,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                ordinal INTEGER DEFAULT nextval('message_ordinal_seq')
                        
            );
            """)
            await self._asyncify(self.con.commit)
        finally:
            await self._asyncify(cur.close)



    async def add_messages(self, turn: str, alr_messages: bytes):
        cur = await self._asyncify(self.con.cursor)
        version = '0.0.1'
        try:
            await self._asyncify(cur.execute, 'BEGIN TRANSACTION')
            try:
                await self._asyncify(
                    cur.execute,
                    'INSERT INTO turns (id, version) VALUES (%s, %s) RETURNING id;',
                    (turn, version)
                )
                turn_id = (await self._asyncify(cur.fetchone))[0]

                await self._asyncify(
                    cur.execute,
                    'INSERT INTO messages (turn_id, message_list) VALUES (%s, %s);',
                    (turn_id, psycopg2.Binary(alr_messages))
                )

                await self._asyncify(self.con.commit)
            except Exception as e:
                await self._asyncify(self.con.rollback)
                raise e
        finally:
            await self._asyncify(cur.close)

    async def get_messages(self) -> list[ModelMessage]:
        c = await self._asyncify(
            self._execute, 'SELECT message_list FROM messages order by id asc'
        )
        rows = await self._asyncify(c.fetchall)
        messages: list[ModelMessage] = []
        for row in rows:
            messages.extend(ModelMessagesTypeAdapter.validate_json(row[0].decode("utf-8")))
        return messages

    async def _get_messages(self) -> list[ModelMessage]:
        cur = await self._asyncify(self.con.cursor)
        try:
            await self._asyncify(cur.execute, """
            SELECT turns.id AS turn_id, turns.ordinal AS turn_ordinal, messages.message_list, messages.ordinal AS message_ordinal, 'alr' AS message_type
            FROM messages
            JOIN turns ON messages.turn_id = turns.id
            ORDER BY turn_ordinal ASC, message_ordinal ASC;
            """)
            rows = await self._asyncify(cur.fetchall)
            messages: list[ModelMessage] = []
            for row in rows:
                message_list = ModelMessagesTypeAdapter.validate_json(bytes(row[2]))
                for message in message_list:
                    messages.append(message)
            return messages
        finally:
            await self._asyncify(cur.close)

    async def get_messages(self) -> tuple[list[ModelMessage], list[ModelMessage]]:
        messages = await self._get_messages()
        return messages


    def _execute(
            self, sql: LiteralString, *args: Any, commit: bool = False
    ) -> psycopg2.extensions.cursor:
        cur = self.con.cursor()
        cur.execute(sql, args)
        if commit:
            self.con.commit()
        return cur

    async def _asyncify(
            self, func: Callable[P, R], *args: P.args, **kwargs: P.kwargs
    ) -> R:
        return await self._loop.run_in_executor(  # type: ignore
            self._executor,
            partial(func, *args, **kwargs),
        )
