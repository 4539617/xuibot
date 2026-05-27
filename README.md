# Xuibot - Telegram Bot for 3x-ui Panel Management

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://docker.com)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=flat&logo=telegram&logoColor=white)](https://core.telegram.org/bots)

Telegram bot for managing 3x-ui panel connections with support for multiple transport protocols and security types.

## ✨ Features

- 🔐 **User Access Request System** - Users request access, admin approves/denies
- ⏰ **Temporary Keys** - Issue time-limited keys (1 hour, 1 day, 3 days, 7 days, 30 days) via admin approval or `/tempkey` command
- 🧹 **Manual Cleanup** - Admin can manually clean up expired keys via /allclients command
- 📝 **Create Keys with Comments** - Custom comments for each connection
- 👥 **User-Key Tracking** - See in panel which Telegram user owns which key
- 📋 **List Your Keys** - View all your active keys with status and traffic usage
- 🔑 **QR Code Generation** - Easy setup with QR codes
- 👑 **Admin Commands** - User management, blocking, removal
- 🛡️ **Anti-Flood Protection** - Limits message frequency from unauthorized users
- 🐳 **Docker Deployment** - Easy setup with Docker
- 🔄 **Multiple Transport Support** - TCP, xHTTP
- 🔒 **Multiple Security Types** - TLS, Reality
- 📊 **Traffic Statistics** - View traffic usage for each key and total consumption
- 🔄 **Auto User Detection** - Automatically adds users with active keys back to the system

## 📋 Commands

### 👤 User Commands
| Command | Description |
|---------|-------------|
| `/start` | Start the bot and check access |
| `/new` | Create a new permanent key |
| `/tempkey` | Create a temporary key (1h, 1d, 3d, 7d, 30d) |
| `/myclients` | List your keys with status and traffic |
| `/help` | Show help |

### 👑 Admin Commands
| Command | Description |
|---------|-------------|
| `/allclients` | View all keys with traffic stats and cleanup expired ones |
| `/users` | List all users |
| `/blockuser` | Block a user |
| `/unblockuser` | Unblock a user |
| `/removeuser` | Remove a user |

### 🎁 Temporary Keys Feature

**Two ways to create temporary keys:**

#### 1. Admin Approval (for new users)
When a user requests access, admin can choose:
- ✅ **Разрешить** - Grant permanent access (user can create unlimited keys)
- 🕐 **Ключ на 1 час** - Issue a single key valid for 1 hour
- 📅 **Ключ на 1 день** - Issue a single key valid for 1 day
- 📅 **Ключ на 3 дня** - Issue a single key valid for 3 days
- 📅 **Ключ на 7 дней** - Issue a single key valid for 7 days
- 📅 **Ключ на 30 дней** - Issue a single key valid for 30 days
- ❌ **Заблокировать** - Block the user

**How it works:**
1. User requests access via `/start`
2. Admin receives notification with buttons
3. Admin selects temporary key duration
4. Bot creates key and sends it to user (QR code + text)
5. Key expires automatically after specified time

**Note:** Temporary keys issued this way don't grant user access to create more keys.

#### 2. `/tempkey` Command (for authorized users)
Authorized users and admins can create temporary keys themselves:
1. Use `/tempkey` command
2. Select duration from menu (1h, 1d, 3d, 7d, 30d)
3. Enter comment for the key
4. Receive QR code and key link
5. Key expires automatically after specified time

**Benefits:**
- Users can create temporary keys for testing or short-term use
- No need to contact admin for temporary access
- Keys are automatically marked as temporary (`temp_username_random` format)
- Expired temporary keys can be cleaned up manually

### 🧹 Manual Cleanup
Use `/allclients` command to:
- View statistics (total, active, inactive, expired keys)
- See total traffic consumption across all keys
- View each key with its traffic usage (displayed in MB)
- Manually cleanup all expired temporary keys with one click
- Click "🧹 Очистить просроченные" button to remove all expired temporary keys

### 📊 Traffic Statistics
The bot now displays traffic usage:
- **In `/allclients`**: Each key shows traffic consumption in MB (e.g., "✅ email - comment (10 MB)")
- **Total statistics**: Shows combined traffic usage across all keys
- **Auto-formatting**: Traffic is displayed in appropriate units (B/KB/MB/GB)

### 🔄 Auto User Detection
The bot automatically detects returning users:
- When a user with active keys runs `/start`, they are automatically added back
- Admin receives notification about returning users
- User history is tracked in the database
- No manual intervention needed for users with existing active keys

### 🔐 Access Control
- Users must run `/start` before using `/new` or `/myclients` commands
- Clear error messages guide users to register first
- Prevents unauthorized access attempts

## 🚀 Quick Start

### Prerequisites
- 3x-ui panel installed on your server

# Installation

*Clone the repository*
```bash
git clone https://github.com/4539617/xuibot.git /opt/xuibot
cd /opt/xuibot
```
*Configure environment*
```bash
nano .env
```
*Run installer*
```bash
chmod +x install.sh
sudo ./install.sh
```
*Check logs*
```bash
docker logs -f xuibot
```


# Management Commands
*View logs*
```bash
docker logs -f xuibot
```
*Restart bot*
```bash
docker restart xuibot
```
*Stop bot*
```bash
docker stop xuibot
```
*Start bot*
```bash
docker start xuibot
```
*Reinstall*
```bash
cd /opt/xuibot && sudo ./install.sh
```
*Rebuild the Docker image*
```bash
docker build -t xuibot .
```


# Reinstall with other transport
*Delete container*
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

# Сomplete delete
```bash
docker rm -f xuibot
docker rmi xuibot
rm -rf /opt/xuibot
```


