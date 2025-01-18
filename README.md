# grade12-culminating

## Pre-reqs

docker desktop <br>
python version 3.12 <br>

These environment variables should be set in .env file

```bash
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=chat_data

OPENAI_API_KEY=<secret>
GEO_API_KEY=<secret>
WEATHER_API_KEY=<secret>
```

## setup done once
```bash
python -m venv amanda-chat
source amanda-chat/bin/activate
pip install -r requirements.txt
```

## Setup up the data source

### the data stuff - in a seperate terminal
```bash
# in a seperate terminal
docker compose up

# when done - to shut down 
ctrl + c
docker compose down

# to reset the databases
docker volume rm grade12-culminating_postgres_data
docker volume rm grade12-culminating_weaviate_data

# to list volumes
docker volume ls
```

# the server
```bash
source amanda-chat/bin/activate


pip install -r requirements.txt
python server/chat_server.py
```
