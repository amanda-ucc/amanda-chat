# Will hold the chat back end logic
import fastapi
from fastapi.responses import FileResponse
from pathlib import Path
# import logfire
from pydantic_ai import Agent

# @asynccontextmanager
# async def lifespan(_app: fastapi.FastAPI):
#     async with Database.connect() as db:
#         yield {'db': db}

app = fastapi.FastAPI()  #(lifespan=lifespan)
# logfire.instrument_fastapi(app)

# agent = Agent('openai:gpt-4o')
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



if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        'chat_server:app', reload=True, reload_dirs=[str(FRONTEND_DIR)]
    )