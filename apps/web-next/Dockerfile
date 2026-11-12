# syntax=docker/dockerfile:1

FROM node:24-alpine AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
ENV LEFTHOOK="0"
RUN corepack enable
WORKDIR /repo

FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web-next/package.json ./apps/web-next/package.json
RUN pnpm install --frozen-lockfile

FROM base AS builder
COPY --from=deps /repo/node_modules ./node_modules
COPY --from=deps /repo/apps/web-next/node_modules ./apps/web-next/node_modules
COPY . .
RUN pnpm --filter web-next build

FROM base AS runner
ENV NODE_ENV="production"
WORKDIR /repo
COPY --from=builder /repo/apps/web-next/.next/standalone ./
COPY --from=builder /repo/apps/web-next/.next/static ./apps/web-next/.next/static
COPY --from=builder /repo/apps/web-next/public ./apps/web-next/public
EXPOSE 3000
CMD ["node", "apps/web-next/server.js"]
