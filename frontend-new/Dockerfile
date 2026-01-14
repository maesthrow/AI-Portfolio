# syntax=docker/dockerfile:1
FROM node:20-alpine AS base
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1

# ---------- deps ----------
FROM base AS deps
COPY package*.json ./
RUN npm ci

# ---------- dev ----------
FROM base AS dev
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["npm","run","dev","--","-H","0.0.0.0","-p","3000"]

# ---------- build ----------
FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Важно: NEXT_PUBLIC_* должны быть доступны на этапе build
ARG NEXT_PUBLIC_CONTENT_API_BASE
ARG NEXT_PUBLIC_AGENT_API_BASE
ARG NEXT_PUBLIC_CHARS_PER_SECOND
ARG NEXT_PUBLIC_MAX_CHARS_PER_TICK

ENV NEXT_PUBLIC_CONTENT_API_BASE=$NEXT_PUBLIC_CONTENT_API_BASE \
    NEXT_PUBLIC_AGENT_API_BASE=$NEXT_PUBLIC_AGENT_API_BASE \
    NEXT_PUBLIC_CHARS_PER_SECOND=$NEXT_PUBLIC_CHARS_PER_SECOND \
    NEXT_PUBLIC_MAX_CHARS_PER_TICK=$NEXT_PUBLIC_MAX_CHARS_PER_TICK

RUN npm run build

# ---------- prod runner ----------
FROM base AS runner
ENV NODE_ENV=production

COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next

EXPOSE 3000
CMD ["npm","run","start","--","-p","3000"]
