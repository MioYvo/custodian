FROM python:alpine

FROM python:alpine

COPY requirements.txt /watchmen/
#COPY rclone-current-linux-amd64.zip /

RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories \
    && apk add -u --no-cache tzdata mariadb-client \
    && apk add --no-cache --virtual .build-deps \
    curl \
    && mkdir /tmp_unzip_dir_for_rclone \
    && curl -O https://downloads.rclone.org/rclone-current-linux-amd64.zip \
    && unzip rclone-current-linux-amd64.zip -d /tmp_unzip_dir_for_rclone \
    && cd /tmp_unzip_dir_for_rclone/* \
    && cp rclone /usr/bin/rclone.new \
    && chmod 755 /usr/bin/rclone.new \
    && chown root:root /usr/bin/rclone.new \
    && mv /usr/bin/rclone.new /usr/bin/rclone \
    && cd / \
    && rm -rf /tmp_unzip_dir_for_rclone \
    && pip install -i https://mirrors.aliyun.com/pypi/simple/ --no-cache-dir -r /watchmen/requirements.txt \
    && apk del --no-cache --purge .build-deps

COPY . /custodian

WORKDIR /custodian

CMD ["python", "-u", "main.py"]
