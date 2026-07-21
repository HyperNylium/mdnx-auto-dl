FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev


FROM debian:trixie-slim AS ffmpeg

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl xz-utils && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /tmp/ff && \
    curl -fL --retry 5 --retry-all-errors --connect-timeout 10 \
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz" | \
    tar -xJ --strip-components=1 -C /tmp/ff && \
    mv /tmp/ff/bin/ffmpeg /usr/local/bin/ffmpeg && \
    mv /tmp/ff/bin/ffprobe /usr/local/bin/ffprobe && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe && \
    rm -rf /tmp/ff


FROM debian:trixie-slim AS bento4

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl unzip && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /tmp/bento4 && \
    curl -fL --retry 5 --retry-all-errors --connect-timeout 10 \
        -o /tmp/bento4.zip \
        "https://www.bok.net/Bento4/binaries/Bento4-SDK-1-6-0-641.x86_64-unknown-linux.zip" && \
    unzip -q /tmp/bento4.zip -d /tmp/bento4 && \
    mv /tmp/bento4/Bento4-SDK-1-6-0-641.x86_64-unknown-linux/bin/mp4decrypt /usr/local/bin/mp4decrypt && \
    chmod +x /usr/local/bin/mp4decrypt && \
    rm -rf /tmp/bento4 /tmp/bento4.zip


FROM debian:trixie-slim AS shaka

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

RUN curl -fL --retry 5 --retry-all-errors --connect-timeout 10 \
        -o /usr/local/bin/shaka \
        "https://github.com/stratumadev/shaka-packager/releases/latest/download/shaka_decrypt-linux-x64" && \
    chmod +x /usr/local/bin/shaka


FROM debian:trixie-slim AS dovi_tool

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

RUN TAG="$(curl -fsSLI -o /dev/null -w '%{url_effective}' \
        "https://github.com/quietvoid/dovi_tool/releases/latest" | sed 's#.*/tag/##')" && \
    mkdir -p /tmp/dovi && \
    curl -fL --retry 5 --retry-all-errors --connect-timeout 10 \
        "https://github.com/quietvoid/dovi_tool/releases/download/${TAG}/dovi_tool-${TAG}-x86_64-unknown-linux-musl.tar.gz" | \
    tar -xz -C /tmp/dovi && \
    mv /tmp/dovi/dovi_tool /usr/local/bin/dovi_tool && \
    chmod +x /usr/local/bin/dovi_tool && \
    rm -rf /tmp/dovi


FROM debian:trixie-slim AS hdr10plus_tool

RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

RUN TAG="$(curl -fsSLI -o /dev/null -w '%{url_effective}' \
        "https://github.com/quietvoid/hdr10plus_tool/releases/latest" | sed 's#.*/tag/##')" && \
    mkdir -p /tmp/hdr10plus && \
    curl -fL --retry 5 --retry-all-errors --connect-timeout 10 \
        "https://github.com/quietvoid/hdr10plus_tool/releases/download/${TAG}/hdr10plus_tool-${TAG}-x86_64-unknown-linux-musl.tar.gz" | \
    tar -xz -C /tmp/hdr10plus && \
    mv /tmp/hdr10plus/hdr10plus_tool /usr/local/bin/hdr10plus_tool && \
    chmod +x /usr/local/bin/hdr10plus_tool && \
    rm -rf /tmp/hdr10plus


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
        gosu && \
    apt-get purge -y --auto-remove wget gnupg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
USER root

COPY --from=builder /app/.venv /app/.venv
COPY --from=ffmpeg /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg /usr/local/bin/ffprobe /usr/local/bin/ffprobe
COPY --from=bento4 /usr/local/bin/mp4decrypt /app/appdata/bin/bento4/mp4decrypt
COPY --from=shaka /usr/local/bin/shaka /app/appdata/bin/shaka_packager/shaka
COPY --from=dovi_tool /usr/local/bin/dovi_tool /app/appdata/bin/dovi_tool/dovi_tool
COPY --from=hdr10plus_tool /usr/local/bin/hdr10plus_tool /app/appdata/bin/hdr10plus_tool/hdr10plus_tool

ENV PATH="/app/.venv/bin:$PATH"

COPY app/ .
COPY pyproject.toml ./

RUN find /app -type f \( -name "*.sh" -o -name "*.py" \) -exec sed -i 's/\r$//' {} + && \
    find /app -type f -name "*.sh" -exec chmod +x {} +

ENTRYPOINT ["/app/entrypoint.sh"]
