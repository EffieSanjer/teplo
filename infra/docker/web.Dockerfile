FROM node:22-alpine AS build
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM nginx:1.27-alpine
COPY infra/docker/nginx.conf /etc/nginx/origin.conf.template
COPY infra/docker/15-origin.sh /docker-entrypoint.d/15-origin.sh
RUN chmod +x /docker-entrypoint.d/15-origin.sh
COPY --from=build /web/dist /usr/share/nginx/html
EXPOSE 80
