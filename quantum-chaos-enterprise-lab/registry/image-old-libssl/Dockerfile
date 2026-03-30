FROM ubuntu:18.04
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        openssl \
        libssl1.0.0 \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*
LABEL quirk.lab="image-old-libssl" \
      quirk.openssl-version="1.0.2n"
CMD ["/bin/bash", "-c", "openssl version && sleep infinity"]
