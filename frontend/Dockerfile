FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production server using lightweight Caddy / Nginx or Node preview
FROM node:20-alpine AS runner

WORKDIR /app

COPY --from=builder /app/dist ./dist
COPY package*.json ./
RUN npm install --omit=dev vite

EXPOSE 5173

CMD ["npx", "vite", "preview", "--host", "0.0.0.0", "--port", "5173"]
