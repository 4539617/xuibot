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
    echo -e "${GREEN}✅ Docker установлен${NC}"
fi

# Создаём директорию для бота
mkdir -p /opt/3xui-bot/{logs,data}
cd /opt/3xui-bot

# Проверяем наличие .env файла
if [ -f ".env" ]; then
    echo -e "${GREEN}✅ Найден существующий .env файл${NC}"
    echo -e "${YELLOW}Использую данные из .env${NC}"
else
    echo -e "\n${BLUE}📝 Введите данные для настройки:${NC}\n"
    
    # Запрос данных с проверкой на пустоту
    while [ -z "$BOT_TOKEN" ]; do
        read -p "BOT_TOKEN (получите у @BotFather): " BOT_TOKEN
    done
    
    while [ -z "$ADMIN_IDS" ]; do
        read -p "ADMIN_IDS (ваш Telegram ID): " ADMIN_IDS
    done
    
    read -p "ADMIN_USERNAME (опционально, например @username): " ADMIN_USERNAME
    
    while [ -z "$XUI_URL" ]; do
        read -p "XUI_URL (полный URL панели): " XUI_URL
    done
    
    while [ -z "$XUI_USERNAME" ]; do
        read -p "XUI_USERNAME (логин панели): " XUI_USERNAME
    done
    
    while [ -z "$XUI_PASSWORD" ]; do
        read -p "XUI_PASSWORD (пароль панели): " XUI_PASSWORD
    done
    
    read -p "INBOUND_ID (ID входящего подключения) [1]: " INBOUND_ID
    INBOUND_ID=${INBOUND_ID:-1}
    
    while [ -z "$SERVER_ADDRESS" ]; do
        read -p "SERVER_ADDRESS (IP или домен сервера): " SERVER_ADDRESS
    done
    
    # Создаём .env файл
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
SNI=yahoo.com
FINGERPRINT=chrome
MAX_TRAFFIC_GB=1000
MAX_DAYS=3650
MIN_DAYS=1
DEFAULT_TRAFFIC_GB=100
DEFAULT_DAYS=30
EOF
    
    echo -e "${GREEN}✅ .env файл создан${NC}"
fi

# Копируем файлы бота из репозитория
echo -e "${YELLOW}📥 Копирование файлов бота...${NC}"
if [ -d "/opt/xuibot" ]; then
    cp -f /opt/xuibot/bot.py /opt/xuibot/config.py /opt/xuibot/utils.py /opt/xuibot/requirements.txt /opt/xuibot/Dockerfile /opt/xuibot/docker-compose.yml /opt/3xui-bot/ 2>/dev/null
    echo -e "${GREEN}✅ Файлы скопированы из /opt/xuibot${NC}"
else
    echo -e "${RED}❌ Директория /opt/xuibot не найдена!${NC}"
    echo -e "${YELLOW}Убедитесь, что файлы бота доступны${NC}"
    exit 1
fi

# Запуск бота
echo -e "${YELLOW}🐳 Запуск Docker контейнера...${NC}"

# Останавливаем и удаляем старый контейнер, если есть
docker stop 3xui-bot 2>/dev/null || true
docker rm 3xui-bot 2>/dev/null || true

# Сборка образа
docker build -t 3xui-bot . 2>&1

# Запуск контейнера
docker run -d \
  --name 3xui-bot \
  --restart always \
  --network host \
  --env-file .env \
  -v ./logs:/app/logs \
  -v ./data:/app/data \
  -v /etc/x-ui/x-ui.db:/etc/x-ui/x-ui.db:ro \
  3xui-bot

# Проверка
sleep 3

echo -e "\n${GREEN}✅ Установка завершена!${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}📊 Статус бота:${NC}"
docker ps --filter name=3xui-bot

echo -e "\n${YELLOW}📋 Последние логи:${NC}"
docker logs --tail=20 3xui-bot

echo -e "\n${GREEN}🎉 Бот успешно установлен!${NC}"
echo -e "${YELLOW}Для просмотра логов: docker logs -f 3xui-bot${NC}"
echo -e "${YELLOW}Для перезапуска: docker restart 3xui-bot${NC}"
echo -e "${YELLOW}Для остановки: docker stop 3xui-bot${NC}"
