FROM python:alpine

FROM python:alpine

COPY requirements.txt /watchmen/

RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories \
    && apk add -u --no-cache tzdata\
    && apk add --no-cache --virtual .build-deps \
    curl bash \
    && curl https://rclone.org/install.sh | bash
    && pip install -i https://mirrors.aliyun.com/pypi/simple/ --no-cache-dir -r /watchmen/requirements.txt
    && apk del --no-cache --purge .build-deps

COPY . /custodian

WORKDIR /custodian

CMD ["python", "-u", "main.py"]
