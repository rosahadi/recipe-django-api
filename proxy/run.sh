
#!/bin/sh

set -e

echo "🟢 Substituting environment variables in nginx config..."
envsubst < /etc/nginx/default.conf.tpl > /etc/nginx/conf.d/default.conf

echo "🟢 Testing nginx configuration..."
nginx -t

echo "🚀 Starting nginx..."
exec nginx -g 'daemon off;'