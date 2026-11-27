FROM node:22-alpine
WORKDIR /web
# Dependencies are baked into the image; frontend sources are mounted at runtime.
# Rebuild this image only when package.json / package-lock.json change.
COPY frontend/package*.json ./
RUN npm ci
