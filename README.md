## Requirements:
* Python =>3.12
* Poetry

## How to run project locally?

### 1. Cloning repository and transition to a branch
If you`re checking pull-request go to appropriate branch:
- bash
#### git checkout BE-1-init-application

### 2. Setting dependencies 
Poetry automatically creates virtual environment and installs all needed packages:
- bash
#### poetry install

### 3. Activation virtual environment(optionally):
To enter inside created virtual environment, complete:
- bash
#### poetry shell

### 4. Running FastAPI application:
To run this app complete:
- bash
#### python app/main.py
In case if you`re outside the app folder:
- bash
#### poetry run uvicorn app.main:app --reload

After that the application is available by link: 
http://127.0.0.1:8000/
