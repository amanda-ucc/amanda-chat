# grade12-culminating

## Pre-reqs

docker desktop <br>
python version 3.12 <br>

## Setup up the data source

```bash
docker compose up
pip install -r requirements.txt
python chat_server.py

# to shut down 
ctrl + c
docker compose down

# to reset the databases
docker volume rm grade12-culminating_postgres_data
docker volume rm grade12-culminating_weaviate_data

# to list volumes
docker volume ls
