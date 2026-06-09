FROM image-registry.openshift-image-registry.svc:5000/deployment-pipeline/uhd:4.7

ARG GIT_REF=develop
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=America/New_York

RUN apt update \
    && apt install -y pipx net-tools iproute2 gnuradio\
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1002220000 mcpworkers && \
    useradd -m -u 1002220000 -g mcpworkers worker && \
    echo "worker:pippo" | chpasswd

WORKDIR /home/worker

RUN --mount=type=ssh,required=true \
  mkdir -p /root/.ssh \
  && ssh-keyscan github.com > /root/.ssh/known_hosts \
  && git clone git@github.com:wineslab/uhd-mcp.git --branch ${GIT_REF} --depth=1 --single-branch \
  && chown -R worker:mcpworkers /home/worker/uhd-mcp

WORKDIR /home/worker/uhd-mcp
USER worker
ENV PATH="/home/worker/.local/bin:$PATH"
RUN ./setup.sh

CMD ["./start.sh"]
