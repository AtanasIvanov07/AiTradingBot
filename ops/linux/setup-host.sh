#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu LTS VM for the dry-run bot (PROJECT_PLAN.md section 3.7 and
# amendment A1). Works on Azure B2ats v2 (x86, 1 GB RAM) and Oracle Ampere A1 (arm64).
#
# Before running it:
#   1. Create the VM yourself (EU region, Ubuntu LTS, SSH key login), with MFA on the cloud account.
#   2. Clone the private repo to ~/AiTradingBot with a read-only deploy key (GitHub > repo >
#      Settings > Deploy keys). Never put a personal token on the server.
# Then:  sudo bash ~/AiTradingBot/ops/linux/setup-host.sh
set -euo pipefail

if [ "$(id -u)" -ne 0 ] || [ -z "${SUDO_USER:-}" ]; then
    echo "Run with sudo from your normal user: sudo bash ops/linux/setup-host.sh" >&2
    exit 1
fi
REPO_DIR="${REPO_DIR:-/home/${SUDO_USER}/AiTradingBot}"
if [ ! -d "${REPO_DIR}/.git" ]; then
    echo "Clone the repo to ${REPO_DIR} first (see the header of this script)." >&2
    exit 1
fi

echo "== 2 GB swap (the 1 GB VMs are below Freqtrade's advised 2 GB RAM)"
if ! swapon --show | grep -q '^/swapfile'; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "== Packages: Docker, time sync, automatic security updates, firewall"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get -y upgrade
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates curl git python3 chrony unattended-upgrades ufw docker.io docker-compose-v2
systemctl enable --now chrony docker
dpkg-reconfigure -f noninteractive unattended-upgrades
usermod -aG docker "${SUDO_USER}"

echo "== Firewall: SSH only (the bot's API stays on 127.0.0.1; reach FreqUI via an SSH tunnel)"
ufw allow OpenSSH
ufw --force enable

echo "== Private config with fresh random API secrets (Docker: API on 0.0.0.0 inside the container)"
sudo -u "${SUDO_USER}" bash -c \
    "cd '${REPO_DIR}' && PYTHONPATH=src python3 -m aitradingbot.ops.private_config --listen 0.0.0.0"
sudo -u "${SUDO_USER}" mkdir -p "${REPO_DIR}/user_data/logs" "${REPO_DIR}/user_data/backups"

echo "== Watchdog service"
sed -e "s|@REPO_DIR@|${REPO_DIR}|g" -e "s|@USER@|${SUDO_USER}|g" \
    "${REPO_DIR}/ops/linux/aitradingbot-watchdog.service" \
    > /etc/systemd/system/aitradingbot-watchdog.service
systemctl daemon-reload

cat <<EOF

Done. Next (as ${SUDO_USER}; log out and in once so the docker group applies):
  cd ${REPO_DIR}
  docker compose -f ops/docker-compose.yml up -d
  sudo systemctl enable --now aitradingbot-watchdog
  tail -f user_data/logs/watchdog.log
Then add your Telegram token / chat id and Healthchecks URL to user_data/config.private.json,
restart both, and repeat the fire drills (ops/fire-drills.md).
EOF
