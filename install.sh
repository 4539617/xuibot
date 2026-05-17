#!/bin/bash
# install.sh - установщик бота (без запроса данных, только из .env)

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

# Проверяем наличие .env файла в текущей директории
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Файл .env не найден в текущей директории!${NC}"
    echo -e "${YELLOW}Скопируйте .env.example в .env и заполните его${NC}"
    exit 1
fi

# Копируем .env в директорию бота
cp -f .env /opt/3xui-bot/.env
echo -e "${GREEN}✅ .env файл скопирован${NC}"

# Копируем файлы бота
echo -e "${YELLOW}📥 Копирование файлов бота...${NC}"

# Определяем источник файлов
if [ -f "bot.py" ] && [ -f "config.py" ] && [ -f "utils.py" ]; then
    # Файлы в текущей директории
    cp -f bot.py config.py utils.py requirements.txt Dockerfile docker-compose.yml /opt/3xui-bot/ 2>/dev/null
    echo -e "${GREEN}✅ Файлы скопированы из текущей директории${NC}"
elif [ -d "/opt/xuibot" ]; then
    # Файлы из клонированного репозитория
    cp -f /opt/xuibot/bot.py /opt/xuibot/config.py /opt/xuibot/utils.py /opt/xuibot/requirements.txt /opt/xuibot/Dockerfile /opt/xuibot/docker-compose.yml /opt/3xui-bot/ 2>/dev/null
    echo -e "${GREEN}✅ Файлы скопированы из /opt/xuibot${NC}"
else
    echo -e "${RED}❌ Не найдены файлы бота!${NC}"
    exit 1
fi

# Переходим в директорию бота
cd /opt/3xui-bot

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
