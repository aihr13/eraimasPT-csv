#!/usr/bin/env bash
set -euo pipefail

# Named volumes are initially root-owned.
mkdir -p /home/node/.codex /home/node/.npm
chown -R node:node /home/node/.codex /home/node/.npm

# Firewall: temporarily disabled until wslc supports NET_ADMIN.
# /usr/local/bin/init-firewall.sh

echo
echo "== Codex container =="
echo "workspace : /workspace"
echo "ollama    : ${OLLAMA_HOST}"
echo "codex     : $(command -v codex || true)"
echo

# Dev Containers runs terminals as remoteUser; execute its startup command.
exec "$@"
