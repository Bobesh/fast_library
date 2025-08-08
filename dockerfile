FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry
RUN poetry config virtualenvs.create false
COPY pyproject.toml poetry.lock ./

RUN poetry install --only=main --no-root
COPY app/ ./app/
COPY sql/ ./sql/

EXPOSE 8000

CMD ["python", "-m", "app.main"]