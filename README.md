# Xuibot - Telegram Bot for 3x-ui Management

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=flat&logo=telegram&logoColor=white)](https://core.telegram.org/bots)

Telegram bot for managing 3x-ui panel connections with support for multiple transport protocols and security types.

## ✨ Features

- 🔐 **User Access Request System** - Users request access, admin approves/denies
- 📝 **Create Keys with Comments** - Custom comments for each connection
- 📋 **List Your Keys** - View all your active keys with creation dates
- 🔑 **QR Code Generation** - Easy setup with QR codes
- 👑 **Admin Commands** - User management, blocking, removal
- 🛡️ **Anti-Flood Protection** - Limits message frequency from unauthorized users
- 🐳 **Docker Deployment** - Easy setup with Docker
- 🔄 **Multiple Transport Support** - TCP, xHTTP, gRPC, WebSocket
- 🔒 **Multiple Security Types** - TLS, Reality

## 📋 Commands

### 👤 User Commands
| Command | Description |
|---------|-------------|
| `/start` | Start the bot |
| `/new` | Create a new VPN key |
| `/myclients` | List your keys |
| `/help` | Show help |

### 👑 Admin Commands
| Command | Description |
|---------|-------------|
| `/users` | List all users |
| `/blockuser` | Block a user |
| `/unblockuser` | Unblock a user |
| `/removeuser` | Remove a user |

## 🚀 Quick Start

### Prerequisites
- 3x-ui panel installed on your server

### Installation

**Clone the repository**
```bash
git clone https://github.com/4539617/xuibot.git /opt/xuibot
cd /opt/xuibot
```
**Configure environment**
```bash
nano .env
```
**Run installer**
```bash
chmod +x install.sh
sudo ./install.sh
```
**Check logs**
```bash
docker logs -f xuibot
```

**Reinstall with other transport**
```bash
cd /opt/xuibot
docker rm -f xuibot
```
*Configure environment*
```bash
nano .env
```
*Run after configuring*
```bash
sudo ./install.sh
```

### Management Commands
# View logs
```bash
docker logs -f xuibot
```
# Restart bot
```bash
docker restart xuibot
```
# Stop bot
```bash
docker stop xuibot
```
# Start bot
```bash
docker start xuibot
```
# Reinstall
```bash
cd /opt/xuibot && sudo ./install.sh
```


