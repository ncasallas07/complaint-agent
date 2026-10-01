#!/bin/bash
# User data para EC2 (Ubuntu 24.04): instala y arranca ComplaintAgent AI en el puerto 8000.
# Log de ejecución: /var/log/cloud-init-output.log
set -eux

apt-get update -y
apt-get install -y python3-venv python3-pip git

cd /home/ubuntu
sudo -u ubuntu git clone https://github.com/ncasallas07/complaint-agent.git
cd complaint-agent
sudo -u ubuntu python3 -m venv venv
sudo -u ubuntu ./venv/bin/pip install --upgrade pip
sudo -u ubuntu ./venv/bin/pip install -r requirements.txt
sudo -u ubuntu cp .env.example .env

cat > /etc/systemd/system/complaint-agent.service <<'EOF'
[Unit]
Description=ComplaintAgent AI (FastAPI/Uvicorn)
After=network-online.target
Wants=network-online.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/complaint-agent
ExecStart=/home/ubuntu/complaint-agent/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now complaint-agent
