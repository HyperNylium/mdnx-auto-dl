FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev


FROM debian:trixie-slim AS ffmpeg

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl xz-utils && \
    rm -rf /var/lib/apt/lists/*

RUN ARCH=$(dpkg --print-architecture) && \
    mkdir -p /tmp/ff && \
    curl -fL "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-${ARCH}-static.tar.xz" | \
    tar -xJ --strip-components=1 -C /tmp/ff && \
    mv /tmp/ff/ffmpeg /usr/local/bin/ffmpeg && \
    mv /tmp/ff/ffprobe /usr/local/bin/ffprobe && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe && \
    rm -rf /tmp/ff


FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        wget \
        gnupg && \
    mkdir -p /etc/apt/keyrings && \
    wget -O /etc/apt/keyrings/gpg-pub-moritzbunkus.gpg \
        https://mkvtoolnix.download/gpg-pub-moritzbunkus.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/gpg-pub-moritzbunkus.gpg] https://mkvtoolnix.download/debian/ trixie main" \
        > /etc/apt/sources.list.d/mkvtoolnix.download.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        mkvtoolnix \
        gosu \
        unzip && \
    apt-get purge -y --auto-remove wget gnupg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
USER root

COPY --from=builder /app/.venv /app/.venv
COPY --from=ffmpeg /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg /usr/local/bin/ffprobe /usr/local/bin/ffprobe

ENV PATH="/app/.venv/bin:$PATH"

COPY app/ .
COPY pyproject.toml ./

RUN find /app -type f \( -name "*.sh" -o -name "*.py" \) -exec sed -i 's/\r$//' {} + && \
    find /app -type f -name "*.sh" -exec chmod +x {} +

ENTRYPOINT ["/app/entrypoint.sh"]
