# AI Chat Application With RAG used for grade12-culminating

Video showcasing the RAG based chat app.


[![Watch the video](https://github.com/user-attachments/assets/ce3c5ac0-b69e-4510-bfb3-1a90fe21fa28)](https://drive.google.com/file/d/1GCAEEqrMMcU4l4NFHNNZ8Lrd2gs3aNOr/view?usp=drive_link)



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
