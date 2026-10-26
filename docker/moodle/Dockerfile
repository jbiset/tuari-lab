FROM alpine:3.22 AS source
RUN apk add --no-cache git ca-certificates
ARG MOODLE_REVISION=215f44380bdc3ccf852a3a22e34f8423ff64033a
RUN git init /source \
    && cd /source \
    && git remote add origin https://github.com/moodle/moodle.git \
    && git fetch --depth=1 origin "${MOODLE_REVISION}" \
    && test "$(git rev-parse FETCH_HEAD)" = "${MOODLE_REVISION}" \
    && git checkout --detach FETCH_HEAD \
    && rm -rf .git

FROM php:8.3-apache-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates curl gosu libfreetype6-dev libicu-dev libjpeg62-turbo-dev \
       libonig-dev libpng-dev libxml2-dev libzip-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j"$(nproc)" exif gd intl mbstring mysqli opcache soap zip \
    && a2enmod headers rewrite remoteip \
    && rm -rf /var/lib/apt/lists/*
COPY --from=source --chown=root:root /source/ /var/www/html/
COPY docker/moodle/php.ini /usr/local/etc/php/conf.d/99-tuari.ini
COPY docker/moodle/apache.conf /etc/apache2/conf-enabled/tuari.conf
COPY docker/moodle/config.php /var/www/html/config.php
COPY docker/moodle/health.php /var/www/html/health.php
COPY docker/moodle/lab/ /opt/tuari/
RUN chmod +x /opt/tuari/*.sh \
    && mkdir -p /var/moodledata \
    && chown www-data:www-data /var/moodledata \
    && php -r 'foreach (["curl","exif","gd","intl","mbstring","mysqli","soap","sodium","zip"] as $e) { if (!extension_loaded($e)) { fwrite(STDERR, "Missing: $e\n"); exit(1); } }'
WORKDIR /var/www/html
