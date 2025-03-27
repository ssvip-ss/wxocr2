FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

ARG TARGETARCH

# Install build dependencies
RUN apt update && \
    apt install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt install -y build-essential cmake make && \
    apt install -y gcc-10 g++-10 git && \
    apt install -y python3.9 python3.9-dev

# Set GCC 10 as default
RUN update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-10 100 && \
    update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-10 100 && \
    update-alternatives --set gcc /usr/bin/gcc-10 && \
    update-alternatives --set g++ /usr/bin/g++-10

# Build
COPY ./wechat-ocr /build

WORKDIR /build

RUN mkdir build && \
    cd build && \
    if [ "${TARGETARCH}" = "arm64" ]; then \
      export LIB_ARCH="aarch64"; \
    else \
      export LIB_ARCH="x86_64"; \
    fi && \
    cmake .. \
      -DPython_EXECUTABLE=/usr/bin/python3.9 \
      -DPython_ROOT=/usr \
      -DPython_INCLUDE_DIR=/usr/include/python3.9 \
      -DPython_LIBRARY=/usr/lib/${LIB_ARCH}-linux-gnu/libpython3.9.so && \
    make pywcocr -j$(nproc)

FROM ubuntu:22.04 AS extractor

COPY ./wx.tar.gz /tmp/wx.tar.gz

RUN tar -zxvf /tmp/wx.tar.gz -C /

FROM python:3.9-slim

ARG TARGETARCH

RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install flask

# Copy architecture-specific files
COPY --from=extractor /wx/${TARGETARCH}/opt /app/wx/opt

# Copy architecture-specific .so files
COPY --from=builder /build/build/wcocr.cpython-*-linux-gnu.so /app/

COPY main.py /app/main.py

WORKDIR /app

CMD ["python", "main.py"]
