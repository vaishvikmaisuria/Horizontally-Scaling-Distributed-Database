# FROM tiangolo/meinheld-gunicorn-flask:python3.7
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7

WORKDIR /app

ADD ./app /app

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt