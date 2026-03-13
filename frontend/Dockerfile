FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npx vite build

# ── Production stage ─────────────────────────────────────────
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# Place template in /etc/nginx/templates/ — the official nginx entrypoint
# automatically runs envsubst on *.template files and outputs to /etc/nginx/conf.d/
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY docker-entrypoint-override.sh /docker-entrypoint-override.sh
RUN chmod +x /docker-entrypoint-override.sh

EXPOSE 80

# Override entrypoint to inject RESOLVER from /etc/resolv.conf before
# the official nginx entrypoint processes templates
ENTRYPOINT ["/docker-entrypoint-override.sh"]
CMD ["nginx", "-g", "daemon off;"]
