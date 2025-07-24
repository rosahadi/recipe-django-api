FROM python:3.12-alpine

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

# Set environment variables for Python and pip
ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Copy requirements and scripts
COPY ./requirements.txt /tmp/requirements.txt
COPY ./requirements.dev.txt /tmp/requirements.dev.txt
COPY ./scripts /scripts
COPY ./app /app

# Set working directory and expose port
WORKDIR /app
EXPOSE 8000

# Build argument for development mode
ARG DEV=false

# Install dependencies and create user
RUN apk add --no-cache \
    postgresql-client \
    zlib-dev \
    libjpeg \
    libpq \
    openssl-dev \
    libffi-dev \ 
    && apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    postgresql-dev \
    libc-dev \
    linux-headers \
    libjpeg-turbo-dev \
    && pip install --upgrade pip \
    && pip install -r /tmp/requirements.txt \
    && if [ $DEV = "true" ]; \
        then pip install -r /tmp/requirements.dev.txt ; \
    fi \
    && rm -rf /tmp \
    && apk del .build-deps \
    && adduser \
        --disabled-password \
        --no-create-home \
        django-user \
    && mkdir -p /vol/web/media /vol/web/static \
    && chown -R django-user:django-user /vol \
    && chmod -R 755 /vol \
    && chmod -R +x /scripts

# Add scripts to PATH for easy execution
ENV PATH="/scripts:$PATH"

# Switch to non-root user
USER django-user

# Default command to run the application
CMD ["run.sh"]