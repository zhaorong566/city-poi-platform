FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

**`backend/requirements.txt`**
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.30
geoalchemy2==0.14.6
psycopg2-binary==2.9.9
alembic==1.13.1
pydantic-settings==2.2.1
redis==5.0.4
httpx==0.27.0