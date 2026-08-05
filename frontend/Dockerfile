# Build stage
FROM node:18-alpine AS build

WORKDIR /app
COPY package.json ./
# --include=dev penting: react-scripts/tailwind ada di devDependencies
RUN npm install --include=dev
COPY . .
RUN npm run build

# Serve stage
FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
