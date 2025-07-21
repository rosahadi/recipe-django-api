FROM nginxinc/nginx-unprivileged:1.27-alpine

COPY ./default.conf.tpl /etc/nginx/default.conf.tpl
COPY ./uwsgi_params /etc/nginx/uwsgi_params
COPY ./run.sh /run.sh

# Environment variables for nginx configuration
ENV LISTEN_PORT=8000
ENV APP_HOST=app
ENV APP_PORT=9000

# Switch to root to make necessary changes
USER root

# Create static volume directory and set permissions
RUN mkdir -p /vol/static && \
    chmod 755 /vol/static && \
    touch /etc/nginx/conf.d/default.conf && \
    chown nginx:nginx /etc/nginx/conf.d/default.conf && \
    chmod +x /run.sh

# Create volume for static files
VOLUME /vol/static

# Switch back to nginx user for security
USER nginx

# Run the startup script
CMD ["/run.sh"]