FROM python:3.12-slim

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY mock_sis ./mock_sis
RUN mkdir -p /srv/data

# The compose file overrides the command for the mock SIS container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
