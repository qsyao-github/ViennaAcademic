FROM python:3.13-slim

COPY requirements.txt /root/requirements.txt

# apt: magic
RUN apt-get update --yes && \
    apt-get install --yes --no-install-recommends libmagic-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    # python requirements
    pip3 install --no-cache-dir -r /root/requirements.txt && \
    rm /root/requirements.txt

WORKDIR /root