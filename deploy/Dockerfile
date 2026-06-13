# USRP MCP Server container image.
#
# Builds UHD from source on a public Ubuntu base so the image is self-contained and
# reproducible. The UHD version is selectable at build time.
#
# Tested with UHD versions: 4.7.0.0, 4.8.0.0
# Known NOT to work: 4.3.0.0
#
#   docker build -f deploy/Dockerfile --build-arg UHD_VERSION=4.7.0.0 -t uhd-mcp:4.7 .
#   docker run --rm --network host -v "$PWD/shared-data:/data/shared" uhd-mcp:4.7
#
FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
ARG UHD_VERSION=4.7.0.0
ARG CMAKE_VERSION=3.22.0
# Download FPGA images for networked USRPs (X3x0/N3xx). Set to "false" to skip.
ARG DOWNLOAD_UHD_IMAGES=true
ENV TZ=Etc/UTC

# Build dependencies for UHD + GNU Radio (which provides uhd_siggen / uhd_rx_cfile),
# plus the app runtime (pipx for Hatch, networking tools).
RUN apt-get update && apt-get install -y \
    autoconf \
    automake \
    build-essential \
    ca-certificates \
    ccache \
    cpufrequtils \
    doxygen \
    ethtool \
    g++ \
    git \
    gnuradio \
    iproute2 \
    libboost-all-dev \
    libncurses-dev \
    libncurses6 \
    libusb-1.0-0 \
    libusb-1.0-0-dev \
    libusb-dev \
    net-tools \
    pipx \
    python3-dev \
    python3-mako \
    python3-numpy \
    python3-requests \
    python3-ruamel.yaml \
    python3-scipy \
    python3-setuptools \
    wget \
  # Pin a specific CMake version (Ubuntu's default may not match the chosen UHD).
  # Download the tarball matching the build architecture (x86_64 or aarch64).
  && apt-get remove -y --purge cmake || true \
  && cd /opt \
  && case "$(uname -m)" in \
       x86_64) CMAKE_ARCH=linux-x86_64 ;; \
       aarch64|arm64) CMAKE_ARCH=linux-aarch64 ;; \
       *) echo "Unsupported architecture: $(uname -m)" && exit 1 ;; \
     esac \
  && wget -nv https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-${CMAKE_ARCH}.tar.gz \
  && tar -xf cmake-${CMAKE_VERSION}-${CMAKE_ARCH}.tar.gz \
  && rm -f cmake-${CMAKE_VERSION}-${CMAKE_ARCH}.tar.gz \
  && ln -s /opt/cmake-${CMAKE_VERSION}-${CMAKE_ARCH}/bin/* /usr/local/bin/ \
  && rm -rf /var/lib/apt/lists/*

# Build and install UHD from source at the requested version. It installs under
# /usr/local, which precedes /usr on PATH and in ldconfig, so the source-built UHD
# takes precedence over the libuhd that the gnuradio apt package pulled in.
RUN git clone https://github.com/EttusResearch/uhd.git /tmp/uhd \
  && cd /tmp/uhd \
  && git checkout v${UHD_VERSION} \
  && cd host \
  && mkdir build \
  && cd build \
  && cmake .. \
  && make -j"$(nproc)" \
  && make install \
  && ldconfig \
  && rm -rf /tmp/uhd

# FPGA images for networked USRPs (optional; large download).
RUN if [ "$DOWNLOAD_UHD_IMAGES" = "true" ]; then uhd_images_downloader || true; fi

# Application code (copied from the build context — no clone or token required).
WORKDIR /app
COPY . /app

# Run as a non-root user. On OpenShift an arbitrary UID (gid 0) is injected, so make
# /app and the data dir group-writable and route HOME to a writable location.
ENV HOME=/app \
    MCP_SHARED_DATA_DIR=/data/shared \
    PATH="/app/.local/bin:${PATH}"
# Ubuntu 24.04 ships a default "ubuntu" user at UID 1000; remove it so we can claim 1000.
RUN userdel -r ubuntu 2>/dev/null || true \
  && useradd -m -u 1000 mcp \
  && mkdir -p /data/shared \
  && chown -R 1000:0 /app /data/shared \
  && chmod -R g+rwX /app /data/shared

USER 1000
RUN ./setup.sh

VOLUME ["/data/shared"]
EXPOSE 8080
CMD ["./start.sh"]
