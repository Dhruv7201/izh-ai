FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install --no-install-recommends curl -y \
        build-essential && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ADD https://astral.sh/uv/install.sh /install.sh
RUN chmod -R 744 /install.sh && /install.sh && rm /install.sh

# Set up the UV environment path correctly
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

COPY . .

RUN uv sync

ENV PATH="/app/.venv/bin:${PATH}"
ENV VIRTUAL_ENV="/app/.venv"
ENV PYTHONPATH="/app/.venv/lib/python3.12/site-packages"

# Expose the specified port for FastAPI
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]