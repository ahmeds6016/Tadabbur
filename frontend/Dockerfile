# Stage 1: Build the Next.js app
FROM node:24-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
RUN npm prune --omit=dev --ignore-scripts

# Stage 2: Serve the app
FROM node:24-alpine
WORKDIR /app
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
ENV NODE_ENV=production
EXPOSE 8080
CMD ["node", "node_modules/next/dist/bin/next", "start", "-p", "8080"]
