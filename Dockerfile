FROM ghcr.io/hypernylium/mdnx-auto-dl-base:latest

COPY app/ .

# Convert Windows line-endings (CRLF) to LF
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
