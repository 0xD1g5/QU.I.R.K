FROM nginx:alpine

# Serve the static orchestrator UI
COPY . /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=3s \
  CMD wget -q -O /dev/null http://localhost:3000 || exit 1
