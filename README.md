## Requirements:
* Python =>3.12
* Poetry

## How to run project locally?

### 1. Cloning repository and transition to a branch
If you're checking pull-request go to appropriate branch:
```bash
    git checkout BE-1-init-application
```
### 2. Setting dependencies 
Poetry automatically creates virtual environment and installs all needed packages:
```bash 
    poetry install
```
### 3. Activation virtual environment(optionally):
To enter inside created virtual environment, complete:
```bash
    poetry shell
```
### 4. Running FastAPI application:
To run this app complete:
```bash
    python app/main.py
```
In case if you're outside the app folder:
```bash
    poetry run uvicorn app.main:app --reload
```
After that the application is available by link: 
http://127.0.0.1:8000/


## How to launch project via Docker?
To build and run the application inside an isolated Docker container, follow these steps:

1. **Build the Docker Image** Run the following command in the root directory (where the `Dockerfile` is located) to download the base image and build your container:
   ```bash
    docker build -t meduzzen-be .
2. Launch the Container Run the container and map the internal port 8000 to your local machine:
   ```bash
   docker run meduzzen-be
   ```
   
 3. Access the Application Once the container is launched, the application will be available at:
   * API Base URL: http://127.0.0.1:8000/
   * Interactive Swagger Docs: http://127.0.0.1:8000/docs

## Databases (PostgreSQL & Redis)
This project uses asynchronous connection to PostgreSQL (via SQLAlchemy + asyncpg) and Redis (via redis-py with asyncio).

### Database's local launch
Ensure that you have full ".env" file in the root of application and then complete:
```bash
   docker compose up -d
```

### Check efficiency
After app's launching go to Swagger documentation page (_/docs_) and complete request for an endpoint _/healthcheck_ for validation of connections. 
