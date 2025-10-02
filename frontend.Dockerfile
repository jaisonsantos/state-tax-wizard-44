FROM node:18-alpine AS build

WORKDIR /app

# Dependências primeiro (melhora cache)
COPY package*.json ./
RUN npm ci

# Código depois (já filtrado pelo .dockerignore do frontend)
COPY . .

# Build
RUN npm run build

# Produção: nginx servindo /dist
FROM nginx:alpine

# Copia build
COPY --from=build /app/dist /usr/share/nginx/html

# Copia config do nginx (vai vir de ./src/nginx.conf)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
