FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
RUN npm install leaflet leaflet.heat axios leaflet-draw @types/leaflet-draw
COPY . .
EXPOSE 5173