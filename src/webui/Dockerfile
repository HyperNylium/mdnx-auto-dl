FROM python:3.13-alpine

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /webui

RUN apk add --no-cache \
    ca-certificates \
    gosu \
    busybox-extras \
    coreutils \
  && update-ca-certificates

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# normalize line endings + executable bit
RUN sed -i 's/\r$//' /webui/entrypoint.sh && chmod +x /webui/entrypoint.sh

EXPOSE 8080
ENTRYPOINT ["/webui/entrypoint.sh"]
