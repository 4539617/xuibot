#!/bin/bash
# install.sh - установщик бота (без запроса данных, только из .env)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    Xuibot Telegram Bot Installer${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Проверка прав
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Запустите с правами root (sudo ./install.sh)${NC}"
    exit 1
fi

# Определяем директорию скрипта (текущая папка репозитория)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${GREEN}📁 Рабочая директория: ${SCRIPT_DIR}${NC}"

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}📦 Установка Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo -e "${GREEN}✅ Docker установлен${NC}"
fi

# Создаём папки для логов и данных
mkdir -p logs data

# Проверяем наличие .env файла
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Файл .env не найден!${NC}"
    echo -e "${YELLOW}Скопируйте .env.example в .env и заполните его${NC}"
    exit 1
fi

echo -e "${GREEN}✅ .env файл найден${NC}"

# Запуск бота
echo -e "${YELLOW}🐳 Запуск Docker контейнера...${NC}"

# Останавливаем и удаляем старый контейнер
docker stop xuibot 2>/dev/null || true
docker rm xuibot 2>/dev/null || true

# Сборка образа
docker build -t xuibot . 2>&1

# Запуск контейнера
docker run -d \
  --name xuibot \
  --restart always \
  --network host \
  --env-file .env \
  -v ./logs:/app/logs \
  -v ./data:/app/data \
  -v /etc/x-ui/x-ui.db:/etc/x-ui/x-ui.db:ro \
  xuibot

# Проверка
sleep 3

echo -e "\n${GREEN}✅ Установка завершена!${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}📊 Статус бота:${NC}"
docker ps --filter name=xuibot

echo -e "\n${YELLOW}📋 Последние логи:${NC}"
docker logs --tail=20 xuibot

echo -e "\n${GREEN}🎉 Бот успешно установлен!${NC}"
echo -e "${YELLOW}Для просмотра логов: docker logs -f xuibot${NC}"
echo -e "${YELLOW}Для перезапуска: docker restart xuibot${NC}"
echo -e "${YELLOW}Для остановки: docker stop xuibot${NC}"
