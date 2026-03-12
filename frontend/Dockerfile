FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npx vite build

# ── Production stage ─────────────────────────────────────────
FROM nginx:alpine

RUN apk add --no-cache gettext

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf.template

EXPOSE 80

# Substitute $BACKEND_URL at runtime, then start nginx
CMD ["/bin/sh", "-c", "envsubst '$BACKEND_URL' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
