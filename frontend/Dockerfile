FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npx vite build

# ── Production stage ─────────────────────────────────────────
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# Official nginx entrypoint substitutes env vars in *.template files
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Defaults — Railway env vars override these at runtime
ENV BACKEND_URL=http://localhost:8000

EXPOSE 80
