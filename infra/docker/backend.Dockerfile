FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY pyproject.toml ./
COPY requirements-dev.lock.txt ./constraints.txt
RUN pip install --no-cache-dir -c constraints.txt fastapi 'uvicorn[standard]' sqlalchemy 'psycopg[binary]' alembic pydantic-settings aiogram python-multipart Pillow beautifulsoup4
COPY src ./src
RUN pip install --no-cache-dir --no-deps . && useradd --create-home app && mkdir -p /data/media && chown app:app /data/media
COPY alembic.ini ./
COPY migrations ./migrations
USER app
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
