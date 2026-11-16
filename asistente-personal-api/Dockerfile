FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig.json ./
COPY src ./src
COPY tests ./tests
COPY scripts ./scripts
RUN npm run build && npm prune --omit=dev

FROM node:22-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app
RUN addgroup -S assistant && adduser -S assistant -G assistant
COPY --from=build --chown=assistant:assistant /app/package.json ./package.json
COPY --from=build --chown=assistant:assistant /app/node_modules ./node_modules
COPY --from=build --chown=assistant:assistant /app/dist ./dist
COPY --chown=assistant:assistant db ./db
USER assistant
EXPOSE 3000
CMD ["node", "dist/src/server.js"]

