FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY benchmarks ./benchmarks
COPY docs ./docs
COPY evals ./evals
COPY policy ./policy
COPY reports ./reports
COPY schemas ./schemas
COPY scripts ./scripts
COPY src ./src
COPY targets ./targets
COPY tests ./tests
COPY traces ./traces

RUN python -m pip install --upgrade pip && python -m pip install ".[dev]"

CMD ["python", "scripts/dev.py", "check"]
