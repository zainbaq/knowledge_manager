# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (better caching)
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Cognito/Amplify config is client-side and gets statically inlined into the JS
# bundle at build time, unlike BACKEND_URL (which is used server-side by the
# next.config.ts rewrite and needs no build-time value). These must be passed as
# build args, not just container runtime env, or the production bundle ships
# with an unconfigured Amplify client and login silently fails.
# BACKEND_URL is consumed by next.config.ts's rewrites(), which Next evaluates
# during the build and bakes into the routes manifest - so it must be a build
# arg. Passing it only as runtime container env leaves the localhost fallback
# baked in and every proxied API call fails with ECONNREFUSED.
ARG BACKEND_URL=http://backend:8000
ENV BACKEND_URL=${BACKEND_URL}

ARG NEXT_PUBLIC_COGNITO_USER_POOL_ID
ARG NEXT_PUBLIC_COGNITO_CLIENT_ID
ARG NEXT_PUBLIC_COGNITO_DOMAIN
ARG NEXT_PUBLIC_REDIRECT_SIGN_IN
ARG NEXT_PUBLIC_REDIRECT_SIGN_OUT
ENV NEXT_PUBLIC_COGNITO_USER_POOL_ID=${NEXT_PUBLIC_COGNITO_USER_POOL_ID}
ENV NEXT_PUBLIC_COGNITO_CLIENT_ID=${NEXT_PUBLIC_COGNITO_CLIENT_ID}
ENV NEXT_PUBLIC_COGNITO_DOMAIN=${NEXT_PUBLIC_COGNITO_DOMAIN}
ENV NEXT_PUBLIC_REDIRECT_SIGN_IN=${NEXT_PUBLIC_REDIRECT_SIGN_IN}
ENV NEXT_PUBLIC_REDIRECT_SIGN_OUT=${NEXT_PUBLIC_REDIRECT_SIGN_OUT}

# API calls go same-origin through the rewrite, so no backend URL is baked in.
RUN npm run build

# Development stage - includes node_modules for hot reload
FROM node:20-alpine AS development

WORKDIR /app

RUN apk add --no-cache curl

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 8501

ENV PORT=8501
ENV HOSTNAME="0.0.0.0"
ENV NODE_ENV=development

CMD ["npm", "run", "dev"]

# Production stage
FROM node:20-alpine AS production

WORKDIR /app

RUN apk add --no-cache curl

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

RUN chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 8501

ENV PORT=8501
ENV HOSTNAME="0.0.0.0"
ENV NODE_ENV=production

CMD ["node", "server.js"]
