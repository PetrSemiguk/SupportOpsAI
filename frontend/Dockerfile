FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.28-alpine
ENV API_UPSTREAM=api:8000 NGINX_ENVSUBST_FILTER=^API_UPSTREAM$
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
