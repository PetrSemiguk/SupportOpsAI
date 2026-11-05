FROM ghcr.io/astral-sh/uv:0.9.7 AS uv
FROM python:3.12.14-slim AS runtime
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend ./backend
COPY data/policies ./data/policies
COPY alembic.ini ./
RUN uv sync --frozen --no-dev && useradd --create-home appuser
USER appuser
EXPOSE 8000
CMD [".venv/bin/uvicorn", "supportops.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
