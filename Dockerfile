FROM python:3.11-slim

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
        gosu && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app/ .

# We will make a non-root user in entrypoint.sh
USER root

# Convert Windows line-endings (CRLF) to LF
RUN sed -i 's/\r$//' /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
