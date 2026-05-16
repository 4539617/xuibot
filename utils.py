# utils.py
import aiohttp
import logging
from typing import Dict
import uuid
import time
import ssl
import json
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)

class XUIClient:
    def __init__(self, config):
        self.config = config
        self.session = None
        self.cookies = None
    
    async def _get_session(self):
        """Создание сессии с SSL контекстом"""
        if self.session is None:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=self.config.xui.api_timeout)
            )
        return self.session
    
    async def login(self) -> bool:
        """Авторизация в панели 3x-ui"""
        await self._get_session()
        
        login_url = f"{self.config.xui.url}/login"
        login_data = {
            "username": self.config.xui.username,
            "password": self.config.xui.password
        }
        
        try:
            async with self.session.post(login_url, json=login_data) as resp:
                if resp.status == 200:
                    self.cookies = self.session.cookie_jar
                    logger.info("Успешная авторизация в 3x-ui")
                    return True
                else:
                    text = await resp.text()
                    logger.error(f"Ошибка авторизации: {resp.status} - {text[:200]}")
                    return False
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return False

    async def add_client(self, email: str, total_gb: int, expiry_days: int, comment: str = None) -> Dict:
        """Создание нового клиента через API 3x-ui с комментарием"""
        if not self.session:
            if not await self.login():
                return {"success": False, "error": "Не удалось авторизоваться"}

        client_uuid = str(uuid.uuid4())
        expiry_time = int((time.time() + expiry_days * 86400) * 1000)
        total_bytes = total_gb * 1024 * 1024 * 1024 if total_gb > 0 else 0

        # Используем комментарий пользователя вместо стандартного
        client_comment = comment if comment else f"Created by bot {time.strftime('%Y-%m-%d %H:%M:%S')}"

        # Формат данных для 3x-ui
        client_data = {
            "id": self.config.xui.inbound_id,
            "settings": json.dumps({
                "clients": [{
                    "id": client_uuid,
                    "email": email,
                    "limitIp": 0,
                    "totalGB": total_bytes,
                    "expiryTime": expiry_time,
                    "enable": True,
                    "flow": "xtls-rprx-vision",
                    "tgId": "",
                    "subId": "",
                    "comment": client_comment
                }]
            })
        }

        # Пробуем разные эндпоинты
        base_url = self.config.xui.url.rstrip('/')
        endpoints = [
            f"{base_url}/xui/API/inbounds/addClient",
            f"{base_url}/panel/api/inbounds/addClient",
            f"{base_url}/server/addClient",
        ]
        
        for endpoint in endpoints:
            try:
                logger.info(f"Пробуем endpoint: {endpoint}")
                async with self.session.post(endpoint, json=client_data) as resp:
                    response_text = await resp.text()
                    logger.info(f"Ответ: {resp.status} - {response_text[:200]}")
                    
                    if resp.status == 200:
                        try:
                            result = json.loads(response_text)
                            if result.get('success') or result.get('obj'):
                                logger.info(f"Клиент {email} создан через {endpoint}")
                                return {"success": True, "uuid": client_uuid}
                        except:
                            pass
                        return {"success": True, "uuid": client_uuid}
                    elif resp.status == 301 or resp.status == 302:
                        # Редирект - пробуем следующий
                        continue
            except Exception as e:
                logger.error(f"Ошибка на {endpoint}: {e}")
                continue
        
        # Если API не работает, пробуем добавить через прямую команду на сервере
        logger.warning("API не работает, пробуем добавить через серверную команду")
        return await self.add_client_via_ssh(email, total_gb, expiry_days, client_uuid)
    
    async def add_client_via_ssh(self, email: str, total_gb: int, expiry_days: int, client_uuid: str) -> Dict:
        """Добавление клиента через SSH команду (обходной путь)"""
        import asyncio
        import subprocess
        
        expiry_time = int((time.time() + expiry_days * 86400))
        total_bytes = total_gb * 1024 * 1024 * 1024 if total_gb > 0 else 0
        
        # Формируем SQL запрос
        sql = f"""sqlite3 /etc/x-ui/x-ui.db "INSERT INTO clients (inbound_id, email, id, enable, limit_ip, total_gb, expiry_time, flow, comment) VALUES ({self.config.xui.inbound_id}, '{email}', '{client_uuid}', 1, 0, {total_bytes}, {expiry_time * 1000}, 'xtls-rprx-vision', 'Created by bot {time.strftime('%Y-%m-%d %H:%M:%S')}');" """
        
        try:
            # Выполняем команду через SSH на сервере
            # Предполагаем что бот запущен на том же сервере
            result = subprocess.run(sql, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Клиент {email} добавлен напрямую в БД")
                return {"success": True, "uuid": client_uuid}
            else:
                logger.error(f"Ошибка добавления в БД: {result.stderr}")
                return {"success": False, "error": f"Ошибка БД: {result.stderr}"}
        except Exception as e:
            logger.error(f"Ошибка выполнения SQL: {e}")
            return {"success": False, "error": str(e)}

    async def delete_client(self, client_uuid: str) -> bool:
        """Удаление клиента через API"""
        if not self.session:
            if not await self.login():
                return False

        base_url = self.config.xui.url.rstrip('/')

        # Пробуем разные эндпоинты для удаления
        endpoints = [
            f"{base_url}/panel/api/inbounds/delClient",
            f"{base_url}/xui/API/inbounds/delClient",
        ]

        for endpoint in endpoints:
            try:
                data = {"id": self.config.xui.inbound_id, "clientId": client_uuid}
                logger.info(f"Пробуем удалить через: {endpoint}")
                async with self.session.post(endpoint, json=data) as resp:
                    response_text = await resp.text()
                    logger.info(f"Ответ: {resp.status} - {response_text[:200]}")
                    if resp.status == 200:
                        logger.info(f"Клиент {client_uuid} удален")
                        return True
            except Exception as e:
                logger.error(f"Ошибка удаления: {e}")
                continue

        # Если API не помог, пробуем через прямую команду (только если бот на том же сервере)
        logger.warning("Пробуем удалить через прямую команду")
        try:
            import subprocess
            sql = f"""sqlite3 /etc/x-ui/x-ui.db "DELETE FROM inbound_clients WHERE id = '{client_uuid}';" """
            result = subprocess.run(sql, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Клиент {client_uuid} удален из БД")
                return True
            else:
                logger.error(f"Ошибка SQL: {result.stderr}")
        except Exception as e:
            logger.error(f"Ошибка: {e}")

        return False

def generate_vless_link(client_uuid: str, email: str, vpn_config, inbound_id: int) -> str:
    """Генерация VLESS ссылки"""
    return f"vless://{client_uuid}@{vpn_config.server_address}:{vpn_config.server_port}?encryption=none&security={vpn_config.security}&sni={vpn_config.sni}&fp={vpn_config.fingerprint}&type=tcp&flow=xtls-rprx-vision#{email}"

def setup_logging(logging_config):
    log_level = getattr(logging, logging_config.level.upper())
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)
    
    if logging_config.file_enabled:
        try:
            file_handler = RotatingFileHandler(
                logging_config.file_path,
                maxBytes=logging_config.max_size_mb * 1024 * 1024,
                backupCount=logging_config.backup_count
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Ошибка создания лог-файла: {e}")


