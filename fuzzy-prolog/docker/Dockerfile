# Image CLI : fuzzyprolog (REPL / requêtes) et identitylink (dédoublonnage).
#   docker build -f docker/Dockerfile -t fuzzy-prolog:0.1.0 .
#   docker run --rm fuzzy-prolog:0.1.0 identitylink evaluate
#   docker run --rm -v "$PWD/data:/data:ro" fuzzy-prolog:0.1.0 identitylink dedupe /data/fiches.csv --json
#   docker run --rm -it fuzzy-prolog:0.1.0 fuzzyprolog examples/flou.pl
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY examples ./examples
RUN python -m pip install --no-cache-dir . && useradd --create-home --uid 1000 app
USER app
ENTRYPOINT []
CMD ["identitylink", "dedupe"]
