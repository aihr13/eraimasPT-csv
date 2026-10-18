FROM node:22-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Tokyo
ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global
ENV PATH="/usr/local/share/npm-global/bin:${PATH}"
ENV OLLAMA_HOST=http://host.wslc.internal:11434

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl wget git git-lfs gh jq less vim nano zsh sudo \
    procps iproute2 iptables ipset dnsutils netcat-openbsd openssh-client \
    unzip zstd build-essential python3 python3-pip python3-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /usr/local/share/npm-global \
    && chown -R node:node /usr/local/share/npm-global

RUN npm install -g pnpm

RUN npm install -g @openai/codex

RUN npm install -g @anthropic-ai/claude-code

# Installs the Ollama CLI. The Ollama server is not started in this container.
RUN curl -fsSL https://ollama.com/install.sh | sh

# Installs the Antigravity CLI.
RUN curl -fsSL https://antigravity.google/cli/install.sh | bash
ENV PATH="/home/node/.local/bin:${PATH}"

RUN mkdir -p /workspace /home/node/.codex \
    && chown -R node:node /workspace /home/node/.codex

RUN mkdir -p /home/node/.claude \
    && chown -R node:node /workspace /home/node/.claude

# Temporarily disabled until wslc supports --cap-add / NET_ADMIN.
# COPY containerScripts/init-firewall.sh /usr/local/bin/init-firewall.sh
COPY containerScripts/entrypoint.sh /usr/local/bin/entrypoint.sh

# RUN chmod 0755 /usr/local/bin/init-firewall.sh /usr/local/bin/entrypoint.sh \
#     && echo "node ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" \
#        > /etc/sudoers.d/codex-firewall \
#     && chmod 0440 /etc/sudoers.d/codex-firewall
RUN chmod 0755 /usr/local/bin/entrypoint.sh

WORKDIR /workspace

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["sleep", "infinity"]
