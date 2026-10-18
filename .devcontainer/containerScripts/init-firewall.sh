#!/usr/bin/env bash
set -euo pipefail

# Ollama server on the home Mac mini (LAN).
OLLAMA_HOST_IP="192.168.0.12"
OLLAMA_PORT="11434"

# Common development endpoints.
ALLOWED_DOMAINS=(
  "github.com"
  "api.github.com"
  "raw.githubusercontent.com"
  "objects.githubusercontent.com"
  "registry.npmjs.org"
  # Antigravity installer / CLI
  "antigravity.google"
  # Google OAuth
  "accounts.google.com"
  "oauth2.googleapis.com"
  "www.googleapis.com"
  # Antigravity / Gemini backend
  "cloudaicompanion.googleapis.com"
  "cloudcode-pa.googleapis.com"
  "generativelanguage.googleapis.com"
)

iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X

ipset destroy allowed-domains 2>/dev/null || true
ipset create allowed-domains hash:ip timeout 3600

iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

iptables -A INPUT \
  -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT \
  -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# DNS
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 53 -j ACCEPT

# Host Ollama
iptables -A OUTPUT \
  -p tcp -d "${OLLAMA_HOST_IP}" --dport "${OLLAMA_PORT}" -j ACCEPT

resolve_domain() {
  local domain="$1"
  dig +short A "$domain" |
    grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' |
    while read -r ip; do
      ipset add allowed-domains "$ip" timeout 3600 -exist
    done
}

for domain in "${ALLOWED_DOMAINS[@]}"; do
  resolve_domain "$domain"
done

iptables -A OUTPUT \
  -p tcp --dport 443 \
  -m set --match-set allowed-domains dst -j ACCEPT

iptables -A OUTPUT \
  -p tcp --dport 80 \
  -m set --match-set allowed-domains dst -j ACCEPT

iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

iptables -A OUTPUT \
  -j REJECT --reject-with icmp-admin-prohibited

echo "[firewall] enabled"
echo "[firewall] Ollama: ${OLLAMA_HOST_IP}:${OLLAMA_PORT}"
