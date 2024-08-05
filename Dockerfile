FROM python:3-slim

WORKDIR /app

RUN pip install poetry

COPY . .

RUN poetry build -f wheel

RUN pip install dist/*

CMD ["python"]
