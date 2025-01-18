# Will hold the chat back end logic
from __future__ import annotations as _annotations
from contextlib import asynccontextmanager
import fastapi
from fastapi.responses import FileResponse
from pathlib import Path
# import logfire
from pydantic_ai import Agent, ModelRetry, RunContext


import asyncio
import json
from collections.abc import AsyncIterator
from concurrent.futures.thread import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Annotated, Any, Callable, Dict, Literal, Optional, TypeVar, Union
import sys
import os
import uuid
from dotenv import load_dotenv

import fastapi
import logfire
import logging
from httpx import AsyncClient

from fastapi import Body, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel
from typing_extensions import TypedDict
from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from database import Database

## Load environment variables
load_dotenv()

dbname = os.getenv('POSTGRES_DB')
dbuser = os.getenv('POSTGRES_USER')
dbpass = os.getenv('POSTGRES_PASSWORD')
dbhost = 'localhost'
dbport = 5432

@dataclass
class Deps:
    client: AsyncClient

## The llm agent 
agent = Agent(
    'openai:gpt-4o',
    system_prompt=(
        'You are a helpful assistent that can provides answers to many questions. '
        'When a user asks for `help` or `what can you do?` specifically then use the `help` tool and output exactly the text it return.'
        'If a the user asks for `about` or `who are you?` then use the `about` tool and output exactly the text it returns.'
    ), 
    deps_type=Deps, 
    retries=2     
)

# Help tool
@agent.tool
async def help(ctx: RunContext[None]) -> str:
    return f'''I am Amanda AI and I can help with many questions. 
    
            I can assist you with a wide range of tasks, including but not limited to:

               - Answering general knowledge questions.
               - Providing explanations and summaries of complex topics.
               - Suggesting resources for learning or exploring new subjects.
               - Assisting with calculations and data analysis.
               - Offering advice for problem-solving and decision-making.
               - Supporting with writing, editing, and language-related queries.
               - Helping with technology-related questions and issues.
               - Engaging in creative tasks like story generation or brainstorming.

            I can also get you the weather and if you upload a document 
            I can help you to answer questions about them!
            
            Feel free to ask me anything specific you need help with!'''

# About tool
@agent.tool
async def about(ctx: RunContext[None]) -> str:
    return f'''Amanda AI is an AI Agent developed by Amanda Uccello. 
               - Creator of Amanda AI: Amanda Uccello
               - Course: ICS 4U
               - School: Port Credit Secondary School
               - Teacher: Mrs. Kim
               - Date: January 2025
               - Model: GPT-4o
               '''

# Latitute and Longitude tool
@agent.tool
async def get_lat_lng(
    ctx: RunContext[Deps], location_description: str
) -> dict[str, float]:
    """Get latitude and longitude .

    Args:
        ctx: The context.
        location_description: Location description.
    """

    geo_api_key = os.getenv('GEO_API_KEY')

    if geo_api_key is None:
        return {'lat': 51.1, 'lng': -0.1}

    params = {
        'q': location_description,
        'api_key': geo_api_key,
    }
    with logfire.span('calling geocode API', params=params) as span:
        r = await ctx.deps.client.get('https://geocode.maps.co/search', params=params)
        r.raise_for_status()
        data = r.json()
        span.set_attribute('response', data)

    if data:
        return {'lat': data[0]['lat'], 'lng': data[0]['lon']}
    else:
        raise ModelRetry('Could not find the location')

@agent.tool
async def get_weather(ctx: RunContext[Deps], lat: float, lng: float) -> dict[str, Any]:
    """Get the weather at a location.

    Args:
        ctx: The context.
        lat: Latitude of the location.
        lng: Longitude of the location.
    """

    weather_api_key = os.getenv('WEATHER_API_KEY')


    if weather_api_key is None:
        # if no API key is provided, return a dummy response
        return {'temperature': '21 °C', 'description': 'Sunny'}

    params = {
        'apikey': weather_api_key,
        'location': f'{lat},{lng}',
        'units': 'metric',
    }
    with logfire.span('calling weather API', params=params) as span:
        r = await ctx.deps.client.get(
            'https://api.tomorrow.io/v4/weather/realtime', params=params
        )
        r.raise_for_status()
        data = r.json()
        span.set_attribute('response', data)

    values = data['data']['values']
    # https://docs.tomorrow.io/reference/data-layers-weather-codes
    code_lookup = {
        1000: 'Clear, Sunny',
        1100: 'Mostly Clear',
        1101: 'Partly Cloudy',
        1102: 'Mostly Cloudy',
        1001: 'Cloudy',
        2000: 'Fog',
        2100: 'Light Fog',
        4000: 'Drizzle',
        4001: 'Rain',
        4200: 'Light Rain',
        4201: 'Heavy Rain',
        5000: 'Snow',
        5001: 'Flurries',
        5100: 'Light Snow',
        5101: 'Heavy Snow',
        6000: 'Freezing Drizzle',
        6001: 'Freezing Rain',
        6200: 'Light Freezing Rain',
        6201: 'Heavy Freezing Rain',
        7000: 'Ice Pellets',
        7101: 'Heavy Ice Pellets',
        7102: 'Light Ice Pellets',
        8000: 'Thunderstorm',
    }
    return {
        'temperature': f'{values["temperatureApparent"]:0.0f}°C',
        'description': code_lookup.get(values['weatherCode'], 'Unknown'),
    }


## Handle the database connection
@asynccontextmanager
async def lifespan(_app: fastapi.FastAPI):
    async with Database.connect(dbname=dbname, user=dbuser, password=dbpass, host=dbhost, port=dbport) as db:
        await db.create_tables()
        yield {'db': db}

async def get_db(request: Request) -> Database:
    return request.state.db


## Create the FastAPI app
app = fastapi.FastAPI(lifespan=lifespan)
# logfire.instrument_fastapi(app)


## Frontend routes
FRONTEND_DIR = Path(__file__).parent /'frontend'

@app.get('/')
async def index() -> FileResponse:
    return FileResponse((FRONTEND_DIR / 'chat_frontend.html'), media_type='text/html')


@app.get('/chat_app.ts')
async def main_ts() -> FileResponse:
    """Get typescript code for the chat frontend."""
    return FileResponse((FRONTEND_DIR / 'chat_frontend.ts'), media_type='text/plain')

@app.get('/favicon.png')
async def favicon() -> FileResponse:
    return FileResponse(FRONTEND_DIR / 'favicon.png', media_type='image/png')


## Chat application
class ChatMessage(TypedDict):
    """Format of messages sent to the browser."""

    role: Literal['user', 'model']
    timestamp: str
    content: str

def to_chat_message(m: ModelMessage) -> ChatMessage:
    if isinstance(m, UserPromptPart):
        return {
            'role': 'user',
            'timestamp': m.timestamp.isoformat(),
            'content': m.content,
        }

    elif isinstance(m, TextPart):

            return {
                'role': 'model',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'content': '<b>Amanda\'s AI Response:</b><br>' + m.content,
            }
    raise UnexpectedModelBehavior(f'Unexpected message type for chat app: {m}')


@app.get('/chat/')
async def get_chat(database: Database = Depends(get_db)) -> Response:
    msgs = await database.get_messages()

    body = b'\n'
    for m in msgs:

        if isinstance(m, ModelRequest):
            for part in m.parts:
                if isinstance(part, UserPromptPart):
                    body += json.dumps(to_chat_message(part)).encode('utf-8') + b'\n'

        if isinstance(m, ModelResponse):
            for part in m.parts:
                if isinstance(part, TextPart):
                    body += json.dumps(to_chat_message(part)).encode('utf-8') + b'\n'

    resp = Response(
        body,
        media_type='text/plain',
    )
    return resp

@app.post('/chat/')
async def post_chat(
    prompt: Annotated[str, fastapi.Form()], database: Database = Depends(get_db)
) -> StreamingResponse:
    async def stream_messages():

        print(f"Prompt: {prompt}")
        
        # stream the user prompt right away
        yield (
                json.dumps(
                    {
                        'role': 'user',
                        'timestamp': datetime.now(tz=timezone.utc).isoformat(),
                        'content': prompt,
                    }
                ).encode('utf-8')
                + b'\n'
        )

        # get the full chat history so far to pass to llmn
        messages = await database.get_messages()



        # Construct dependencies
        async with AsyncClient() as client:

            deps = Deps(
                client=client
            )
            result_final = await agent.run(prompt, message_history=messages, deps=deps)

            text = result_final.data

            m = ModelResponse.from_text(content=text, timestamp=datetime.now())
            resp = m.parts[0]

            yield json.dumps(to_chat_message(resp)).encode('utf-8') + b'\n'


        # Save messages to the database
        saved_messages_json = result_final.new_messages_json()

        turn_id = str(uuid.uuid4())

        # add new messages to the database
        await database.add_messages(turn_id, saved_messages_json)

    return StreamingResponse(stream_messages(), media_type='text/plain')



if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        'chat_server:app', reload=True, reload_dirs=[str(FRONTEND_DIR)]
    )