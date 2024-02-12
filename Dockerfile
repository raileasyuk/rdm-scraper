FROM python:3.12-alpine

RUN apk add --update ca-certificates # Certificates for SSL
RUN apk add --update tzdata          # Timezone data

WORKDIR /usr/src/app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
COPY *.py .

RUN python -m compileall .

ENTRYPOINT ["python", "scraper.py"]