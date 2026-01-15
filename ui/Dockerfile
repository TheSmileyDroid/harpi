FROM oven/bun:1 AS frontend

WORKDIR /app

COPY package.json bun.lock ./

RUN bun i --production

RUN bun i vite

COPY . .

ENV NODE_ENV='production'

RUN bun --bun run build

EXPOSE 3000/tcp

CMD ["/usr/local/bin/bun", "./build/index.js"]
