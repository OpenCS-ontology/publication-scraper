FROM python:3.10.9-slim-bullseye

COPY requirements.txt /home/scrape/requirements.txt

RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y binutils

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /
COPY ./ ./scraper
WORKDIR /scraper
COPY container_test /container_test

RUN pip3 install wheel && \
    pip3 install -r /home/scrape/requirements.txt

RUN apt-get install git -y \
    && apt-get install wget -y \
    && apt install unzip -y \
    && apt install chromium -y \
    && wget https://chromedriver.storage.googleapis.com/90.0.4430.24/chromedriver_linux64.zip \ 
    && unzip chromedriver_linux64.zip
