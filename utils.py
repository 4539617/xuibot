# utils.py
import aiohttp
import logging
import subprocess
import json
import uuid
import time
import ssl
from typing import Dict
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

        client_comment = comment if comment else f"Created by bot {time.strftime('%Y-%m-%d %H:%M:%S')}"

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
                    elif resp.status in [301, 302]:
                        continue
            except Exception as e:
                logger.error(f"Ошибка на {endpoint}: {e}")
                continue
        
        logger.warning("API не работает, пробуем добавить через SQL")
        return await self.add_client_via_sql(email, total_gb, expiry_days, client_uuid, client_comment)
    
    async def add_client_via_sql(self, email: str, total_gb: int, expiry_days: int, client_uuid: str, client_comment: str) -> Dict:
        """Добавление клиента напрямую в БД"""
        expiry_time = int((time.time() + expiry_days * 86400)) * 1000
        total_bytes = total_gb * 1024 * 1024 * 1024 if total_gb > 0 else 0
        
        # Пробуем разные названия таблиц
        tables = ["clients", "inbound_clients", "client_traffics"]
        
        for table in tables:
            sql = f"""sqlite3 {self.config.xui.db_path} "INSERT INTO {table} (inbound_id, email, id, enable, limit_ip, total_gb, expiry_time, flow, comment) VALUES ({self.config.xui.inbound_id}, '{email}', '{client_uuid}', 1, 0, {total_bytes}, {expiry_time}, 'xtls-rprx-vision', '{client_comment}');" """
            
            try:
                result = subprocess.run(sql, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"Клиент {email} добавлен в таблицу {table}")
                    return {"success": True, "uuid": client_uuid}
            except:
                continue
        
        return {"success": False, "error": "Не удалось создать клиента"}

    async def delete_client(self, client_uuid: str) -> bool:
        """Удаление клиента (просто возвращаем True)"""
        logger.info(f"Удаление клиента {client_uuid} (виртуальное)")
        return True


def generate_vless_link(client_uuid: str, email: str, vpn_config, inbound_id: int) -> str:
    """Универсальная генерация VLESS ссылки в зависимости от настроек"""
    
    base = f"vless://{client_uuid}@{vpn_config.server_address}:{vpn_config.server_port}"
    
    params = f"encryption=none&security={vpn_config.security}"
    
    # SNI
    sni = vpn_config.get_sni()
    if sni:
        params += f"&sni={sni}"
    
    # Fingerprint
    params += f"&fp={vpn_config.get_fingerprint()}"
    
    # Reality параметры
    if vpn_config.security == "reality":
        if vpn_config.reality_public_key:
            params += f"&pbk={vpn_config.reality_public_key}"
        if vpn_config.reality_short_id:
            params += f"&sid={vpn_config.reality_short_id}"
    
    # Транспорт
    params += f"&type={vpn_config.transport}"
    
    # xHTTP параметры
    if vpn_config.transport == "xhttp":
        params += f"&mode={vpn_config.xhttp_mode}"
    
    # Flow
    params += "&flow=xtls-rprx-vision"
    
    return f"{base}?{params}#{email}"


def setup_logging(logging_config):
    """Настройка логирования"""
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
