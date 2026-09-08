# Built with the REPO ROOT as build context (not ./frontend) - see
# render.yaml and docker-compose.yml, both of which pass `frontend/...`
# paths below for exactly this reason. See backend/Dockerfile's header
# comment for why.
FROM node:20-alpine AS deps
WORKDIR /app
COPY frontend/package.json ./
RUN npm install

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/. .
RUN mkdir -p public
# NEXT_PUBLIC_* variables are baked into the client JS bundle at build time,
# not read at runtime - so this has to arrive as a build ARG, not just a
# runtime env var. On Render, envVars set on a Docker-runtime service are
# automatically passed through as build args of the same name; the ARG/ENV
# pair here is what actually makes the Dockerfile consume that value (Docker
# silently ignores an unconsumed --build-arg otherwise). For local
# docker-compose builds, this comes from docker-compose.yml's build.args.
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000
CMD ["npm", "start"]
