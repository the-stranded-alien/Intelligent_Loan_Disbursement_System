FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npx vite build

# ── Production stage ─────────────────────────────────────────
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# Template — entrypoint substitutes ${PORT} and ${BACKEND_URL} at runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf.template
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Defaults — Railway env vars override these at runtime
ENV BACKEND_URL=http://localhost:8000
ENV PORT=80

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
