FROM node:22-bookworm-slim

WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN npm install --global "$(node -p 'require("./package.json").packageManager')" \
    && pnpm install --frozen-lockfile

COPY . .
ARG MARKETPLACE_API_URL=http://127.0.0.1:8000
# The page also reads the API address at runtime to load the venue.
ENV MARKETPLACE_API_URL=$MARKETPLACE_API_URL
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build

CMD ["node", "node_modules/next/dist/bin/next", "start", "--hostname", "0.0.0.0"]
