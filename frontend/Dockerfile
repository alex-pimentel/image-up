# syntax=docker/dockerfile:1
FROM node:20-alpine AS build
WORKDIR /app
# git is required to install the @agenteresolve/ui-tokens git dependency.
RUN apk add --no-cache git
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && corepack pnpm install --frozen-lockfile
COPY . .
RUN corepack pnpm build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]