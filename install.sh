
### 3. `install.sh` (установщик):

```bash
#!/bin/bash
# install.sh - установщик бота

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    3x-ui Telegram Bot Installer${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Проверка прав
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Запустите с правами root (sudo ./install.sh)${NC}"
    exit 1
fi

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}📦 Установка Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

# Запрос данных
echo -e "\n${BLUE}📝 Введите данные для настройки:${NC}\n"

read -p "BOT_TOKEN: " BOT_TOKEN
read -p "ADMIN_IDS: " ADMIN_IDS
read -p "ADMIN_USERNAME (опционально): " ADMIN_USERNAME
read -p "XUI_URL: " XUI_URL
read -p "XUI_USERNAME: " XUI_USERNAME
read -p "XUI_PASSWORD: " XUI_PASSWORD
read -p "INBOUND_ID [1]: " INBOUND_ID
INBOUND_ID=${INBOUND_ID:-1}
read -p "SERVER_ADDRESS: " SERVER_ADDRESS

# Создание .env
mkdir -p /opt/3xui-bot
cd /opt/3xui-bot

cat > .env << EOF
BOT_TOKEN=${BOT_TOKEN}
ADMIN_IDS=${ADMIN_IDS}
ADMIN_USERNAME=${ADMIN_USERNAME}
XUI_URL=${XUI_URL}
XUI_USERNAME=${XUI_USERNAME}
XUI_PASSWORD=${XUI_PASSWORD}
INBOUND_ID=${INBOUND_ID}
SERVER_ADDRESS=${SERVER_ADDRESS}
SERVER_PORT=443
SECURITY=tls
SNI=google.com
FINGERPRINT=firefox
MAX_TRAFFIC_GB=1000
MAX_DAYS=3650
MIN_DAYS=1
DEFAULT_TRAFFIC_GB=100
DEFAULT_DAYS=30
EOF

# Копирование файлов бота (из текущей директории)
cp -f bot.py config.py utils.py requirements.txt Dockerfile docker-compose.yml /opt/3xui-bot/ 2>/dev/null

# Запуск
docker build -t 3xui-bot .
docker run -d --name 3xui-bot --restart always --network host --env-file .env \
  -v ./logs:/app/logs -v ./data:/app/data \
  -v /etc/x-ui/x-ui.db:/etc/x-ui/x-ui.db:ro 3xui-bot

echo -e "\n${GREEN}✅ Установка завершена!${NC}"
docker logs --tail=20 3xui-bot
