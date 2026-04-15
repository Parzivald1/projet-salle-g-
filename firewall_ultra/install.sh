#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INSTALL_DIR="/opt/portail-captif"
SERVICE_NAME="portail-captif"
NGINX_CONF="/etc/nginx/sites-available/portail-captif"

echo -e "${BLUE}"
echo "=============================================="
echo "  INTERFACE FORMATEUR - SALLE G"
echo "  Raspberry Pi - Administration uniquement"
echo "=============================================="
echo -e "${NC}"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Erreur: sudo requis${NC}"
    exit 1
fi

# Arrêter les anciens services
echo -e "\n${YELLOW}[0/7] Nettoyage des anciens services...${NC}"
systemctl stop portail-captif 2>/dev/null || true
systemctl stop nginx 2>/dev/null || true
# Forcer la fin des processus Python/Gunicorn encore en mémoire
pkill -f "gunicorn.*app:app" 2>/dev/null || true
pkill -f "python.*app.py" 2>/dev/null || true
sleep 2
# Supprimer l'ancien venv MAINTENANT avant la copie pour eviter "Text file busy"
rm -rf $INSTALL_DIR/venv

echo -e "\n${YELLOW}[1/7] Mise à jour...${NC}"
apt update && apt upgrade -y

echo -e "\n${YELLOW}[2/7] Installation des dépendances...${NC}"
apt install -y python3 python3-pip python3-venv nginx

echo -e "\n${YELLOW}[3/7] Copie des fichiers...${NC}"
mkdir -p $INSTALL_DIR/data

if [ -f "app.py" ]; then
    # Copier uniquement les fichiers du projet, sans venv ni data
    rsync -a --exclude='venv/' --exclude='data/' --exclude='.git/' ./ $INSTALL_DIR/ 2>/dev/null \
    || { cp -r ./* $INSTALL_DIR/ ; rm -rf $INSTALL_DIR/venv ; }
else
    echo -e "${RED}Exécutez depuis le dossier du projet${NC}"
    exit 1
fi

echo -e "\n${YELLOW}[4/7] Python...${NC}"
cd $INSTALL_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "\n${YELLOW}[5/7] Base de données...${NC}"
if [ -f "database/init_db.py" ]; then
    python database/init_db.py
fi

echo -e "\n${YELLOW}[6/7] Nginx (port 80 UNIQUEMENT)...${NC}"
cat > $NGINX_CONF << 'EOF'
server {
    listen 80;
    server_name _;

    access_log /var/log/nginx/portail-captif-access.log;
    error_log /var/log/nginx/portail-captif-error.log;

    # 1. Fichiers statiques du portail
    location /static {
        alias /opt/portail-captif/static;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    # 2. Gestion de la racine. GET = Portail, POST = Login OPNsense
    location = / {
        error_page 418 = @flask;
        if ($request_method = GET) {
            return 418;
        }
        proxy_pass http://192.168.1.1;
        proxy_set_header Host 192.168.1.1;
        proxy_set_header Origin "http://192.168.1.1";
        proxy_set_header Referer "http://192.168.1.1/";
        proxy_hide_header X-Frame-Options;
        proxy_hide_header x-frame-options;
        proxy_hide_header Content-Security-Policy;
    }

    location @flask {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 3. Routes exclusives de l'app Python
    location ~ ^/(connexion-formateur|change-code|admin|zenarmor|logout|api) {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 4. Le reste (Iframe Zenarmor) part vers OPNsense !
    location / {
        proxy_pass http://192.168.1.1;
        proxy_set_header Host 192.168.1.1;
        proxy_set_header Origin "http://192.168.1.1";
        proxy_set_header Referer "http://192.168.1.1$request_uri";
        proxy_hide_header X-Frame-Options;
        proxy_hide_header x-frame-options;
        proxy_hide_header Content-Security-Policy;
    }
}
EOF

ln -sf $NGINX_CONF /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo -e "\n${YELLOW}[7/7] Service...${NC}"
cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=Interface Formateur Salle G
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
ExecStart=$INSTALL_DIR/venv/bin/gunicorn --workers 2 --timeout 60 --bind 127.0.0.1:5000 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME

sleep 2

echo ""
echo -e "${YELLOW}=== Vérification des ports ===${NC}"
echo "Nginx (port 80) :"
ss -tlnp | grep ":80 " || echo "  PAS EN ÉCOUTE"
echo "Gunicorn (port 5000, local) :"
ss -tlnp | grep ":5000" || echo "  PAS EN ÉCOUTE"
echo ""
echo "Ports 8000/8001 (ne devraient PAS être là) :"
ss -tlnp | grep -E ":800[01] " && echo -e "  ${RED}ATTENTION: port 8000/8001 encore actif !${NC}" || echo -e "  ${GREEN}OK - aucun processus sur 8000/8001${NC}"

if systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "\n${GREEN}=============================================="
    echo "  OK ! Interface formateur en ligne"
    echo "=============================================="
    echo -e "${NC}"
    echo -e "  ${BLUE}http://192.168.3.54/admin${NC}"
else
    echo -e "\n${RED}Erreur au démarrage${NC}"
    echo "journalctl -u $SERVICE_NAME"
    exit 1
fi
