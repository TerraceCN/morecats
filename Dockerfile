FROM python:3.9-slim

WORKDIR /app

EXPOSE 8080

COPY requirements.txt /app

RUN sed -i "s/http:\/\/.*\.debian\.org/http:\/\/mirrors.aliyun.com/g" /etc/apt/sources.list && \
    # apt-get update -y && \
    # apt-get install -y libmariadb-dev gcc && \
    pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --no-cache-dir && \
    # apt-get remove -y --auto-remove gcc && \
    apt-get clean

COPY . /app

ENTRYPOINT ["python", "/app/bot.py"]
