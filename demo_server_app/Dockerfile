FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi==0.109.0 uvicorn==0.27.0 pydantic==2.5.3

COPY inventory_api.py ./inventory_api.py
COPY data/ ./data/

ENV INVENTORY_PATH=/app/data/inventory.json
ENV MEDICATIONS_PATH=/app/data/medications.json

EXPOSE 8001

CMD ["python", "-m", "uvicorn", "inventory_api:app", "--host", "0.0.0.0", "--port", "8001"]
