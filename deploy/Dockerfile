# syntax=docker/dockerfile:1
# USRP MCP Server container image — multi-stage build with a selectable UHD source.
#
# Stages:
#   uhd-source    self-contained UHD build from source (no registry access needed)
#   uhd-prebuilt  org base image with UHD already built (ghcr.io/wineslab/uhd)
#   deps          runtime dependencies UHD alone doesn't cover (GNU Radio, pipx,
#                 FPGA images, network tooling) — published as ghcr.io/wineslab/uhd-mcp-deps
#   mcp           the application layer (final stage)
#
# Build recipes:
#   # 1. Normal build on the org UHD base (needs `docker login ghcr.io` while the base is private)
#   docker build -f deploy/Dockerfile -t uhd-mcp .
#
#   # 2. Fast build reusing the published deps image (what release CI does)
#   docker build -f deploy/Dockerfile --build-arg DEPS_IMAGE=ghcr.io/wineslab/uhd-mcp-deps:uhd4.7 -t uhd-mcp .
#
#   # 3. Fully self-contained build, UHD compiled from source (today's classic behavior)
#   docker build -f deploy/Dockerfile --build-arg UHD_FLAVOR=source --build-arg UHD_VERSION=4.7.0.0 -t uhd-mcp .
#
#   # 4. Build/publish just the deps image
#   docker build -f deploy/Dockerfile --target deps -t ghcr.io/wineslab/uhd-mcp-deps:uhd4.7 .
#
# Tested with UHD versions: 4.7.0.0, 4.8.0.0. Known NOT to work: 4.3.0.0.
# The org base image is amd64-only; use UHD_FLAVOR=source for other architectures.
#
#   docker run --rm --network host -v "$PWD/shared-data:/data/shared" uhd-mcp

# ---- Build-mode selectors (all overridable) --------------------------------
# UHD_FLAVOR: "prebuilt" (org base image) or "source" (compile UHD here).
ARG UHD_FLAVOR=prebuilt
ARG UHD_BASE_IMAGE=ghcr.io/wineslab/uhd:4.7
# DEPS_IMAGE: "deps" (build the deps stage locally) or a published deps image ref.
ARG DEPS_IMAGE=deps

# ---- Stage uhd-source: UHD compiled from source on a public base -----------
FROM ubuntu:24.04 AS uhd-source

ARG DEBIAN_FRONTEND=noninteractive
ARG UHD_VERSION=4.7.0.0
ARG CMAKE_VERSION=3.22.0
ENV TZ=Etc/UTC

# Build-time dependencies for UHD only.
RUN apt-get update && apt-get install -y \
    autoconf \
    automake \
    build-essential \
    ca-certificates \
    ccache \
    doxygen \
    g++ \
    git \
    libboost-all-dev \
    libncurses-dev \
    libusb-1.0-0-dev \
    libusb-dev \
    python3-dev \
    python3-mako \
    python3-numpy \
    python3-requests \
    python3-ruamel.yaml \
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

# Build and install UHD from source at the requested version (into /usr/local).
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

# ---- Stage uhd-prebuilt: org base image with UHD already built -------------
FROM ${UHD_BASE_IMAGE} AS uhd-prebuilt

# ---- Stage deps: runtime dependencies the UHD base doesn't provide ---------
FROM uhd-${UHD_FLAVOR} AS deps

ARG DEBIAN_FRONTEND=noninteractive
# Download FPGA images for networked USRPs (X3x0/N3xx). Set to "false" to skip
# (much smaller image; mount the images or run uhd_images_downloader at runtime).
ARG DOWNLOAD_UHD_IMAGES=true
ENV TZ=Etc/UTC

# GNU Radio provides uhd_siggen / uhd_rx_cfile; pipx provides Hatch; the rest is
# networking tooling for reaching Ethernet USRPs. gnuradio apt-pulls a distro
# libuhd into /usr, but the UHD from the stage above lives in /usr/local, which
# precedes /usr on PATH and in ldconfig, so it takes precedence.
RUN apt-get update && apt-get install -y \
    ca-certificates \
    cpufrequtils \
    ethtool \
    gnuradio \
    iproute2 \
    libncurses6 \
    libusb-1.0-0 \
    net-tools \
    pipx \
    python3-numpy \
    python3-requests \
    python3-ruamel.yaml \
    python3-scipy \
    wget \
  && rm -rf /var/lib/apt/lists/*

# FPGA images for networked USRPs (optional; large download).
RUN if [ "$DOWNLOAD_UHD_IMAGES" = "true" ]; then uhd_images_downloader || true; fi

# ---- Final stage: the MCP application ---------------------------------------
FROM ${DEPS_IMAGE} AS mcp

# Application code (copied from the build context — no clone or token required).
WORKDIR /app
COPY . /app

# Run as a non-root user. On OpenShift an arbitrary UID (gid 0) is injected, so make
# /app and the data dir group-writable and route HOME to a writable location.
ENV HOME=/app \
    MCP_SHARED_DATA_DIR=/data/shared \
    PATH="/app/.local/bin:${PATH}" \
    # UHD installs its Python bindings under /usr/local .../site-packages, which
    # neither Ubuntu's python nor the Hatch venv searches. execute_uhd_script
    # whitelists PYTHONPATH into its sandbox, so this makes `import uhd` work.
    PYTHONPATH=/usr/local/lib/python3.12/site-packages
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
