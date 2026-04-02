FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        iputils-ping \
        ffmpeg \
        mkvtoolnix \
        jq \
        gosu \
        unzip && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

USER root

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

RUN find /app -type f \( -name "*.sh" -o -name "*.py" \) -exec sed -i 's/\r$//' {} + && \
    find /app -type f -name "*.sh" -exec chmod +x {} +

ENTRYPOINT ["/app/entrypoint.sh"]
