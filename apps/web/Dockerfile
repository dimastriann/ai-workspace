# syntax=docker/dockerfile:1

FROM node:24-alpine AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
ENV LEFTHOOK="0"
# Public runtime URLs are inlined by Next at build time.
ARG NEXT_PUBLIC_IDE_URL=http://localhost:8091
ARG NEXT_PUBLIC_TERMINAL_URL=http://localhost:8092
ENV NEXT_PUBLIC_IDE_URL=$NEXT_PUBLIC_IDE_URL
ENV NEXT_PUBLIC_TERMINAL_URL=$NEXT_PUBLIC_TERMINAL_URL
RUN apk add --no-cache git && corepack enable
WORKDIR /repo

FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY scripts/install-hooks.mjs ./scripts/install-hooks.mjs
COPY apps/web/package.json ./apps/web/package.json
RUN pnpm install --frozen-lockfile

FROM base AS builder
COPY --from=deps /repo/node_modules ./node_modules
COPY --from=deps /repo/apps/web/node_modules ./apps/web/node_modules
COPY . .
RUN pnpm --filter web build

FROM base AS runner
ENV NODE_ENV="production"
WORKDIR /repo
COPY --from=builder /repo/apps/web/.next/standalone ./
COPY --from=builder /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /repo/apps/web/public ./apps/web/public
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
