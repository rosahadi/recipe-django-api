server {
    listen ${LISTEN_PORT};
    
    # Static files location
    location /static {
        alias /vol/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Main application proxy
    location / {
        uwsgi_pass              ${APP_HOST}:${APP_PORT};
        include                 /etc/nginx/uwsgi_params;
        client_max_body_size    10M;
        
        # Security headers
        add_header X-Content-Type-Options nosniff;
        add_header X-Frame-Options DENY;
        add_header X-XSS-Protection "1; mode=block";
    }
}