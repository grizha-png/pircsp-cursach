FROM nginx:1.27-alpine

ENV PORT=80
ENV BACKEND_URL=http://backend:8000

COPY frontend /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/templates/default.conf.template
