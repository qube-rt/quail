### Build, intermediate container
FROM node:16 as build

WORKDIR /app

COPY frontend/package*.json /app/

ARG NPM_CONFIG_REGISTRY="https://registry.npmjs.org"
RUN npm install --package-lock=true --production=false

COPY frontend/.* *.json /app/
COPY frontend/public /app/public/
COPY frontend/src /app/src/

RUN npm run build

### Serve, target container
FROM nginx
EXPOSE 80

COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/build /usr/share/nginx/html
