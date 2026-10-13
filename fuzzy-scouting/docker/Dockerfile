# Image de l'API HTTP fuzzyscout.
# Construction (depuis la racine du dépôt) :
#   docker build -f docker/Dockerfile -t fuzzy-scouting:0.1.0 .
# Exécution :
#   docker run --rm -p 8000:8000 fuzzy-scouting:0.1.0

FROM python:3.13-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --upgrade pip \
 && python -m pip wheel --no-deps --wheel-dir /wheels .

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FUZZYSCOUT_LOG_LEVEL=INFO
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/*.whl "fastapi>=0.110" "uvicorn[standard]>=0.29" "pydantic>=2.6" \
 && rm -rf /wheels \
 && useradd --create-home --uid 1000 app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status == 200 else 1)"
CMD ["uvicorn", "fuzzyscout.interfaces.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
