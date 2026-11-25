# PlaceIQ: single container for Hugging Face Spaces (or any Docker host).
# Stage 1 builds the Next.js web app; stage 2 runs the Python engine and the web server.

FROM node:22-bookworm-slim AS web
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
ENV NEXT_TELEMETRY_DISABLED=1 PLACEIQ_STANDALONE=1
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    MPLCONFIGDIR=/tmp/matplotlib NEXT_TELEMETRY_DISABLED=1
# Node runtime for the Next.js standalone server
COPY --from=web /usr/local/bin/node /usr/local/bin/node

RUN useradd -m -u 1000 user
WORKDIR /app
COPY requirements-runtime.txt ./
RUN pip install -r requirements-runtime.txt

COPY placeiq/ placeiq/
COPY placeiq-data/ placeiq-data/
# Train on the bundled public datasets at build time, so the model is ready on first start.
# A throwaway salt is used only for this step; set the real one as the PLACEIQ_SALT secret.
RUN PLACEIQ_SALT=build-time-only python -W ignore -m placeiq public

COPY --from=web /app/web/.next/standalone ./web/
COPY --from=web /app/web/.next/static ./web/.next/static
COPY docker/start.sh ./start.sh
RUN chmod +x start.sh && chown -R user:user /app

USER user
ENV PORT=7860 HOSTNAME=0.0.0.0 PLACEIQ_API_URL=http://127.0.0.1:8765 \
    MPLCONFIGDIR=/home/user/.cache/matplotlib
EXPOSE 7860
CMD ["./start.sh"]
