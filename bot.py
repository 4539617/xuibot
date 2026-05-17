import asyncio
import logging
import random
import string
from io import BytesIO
from datetime import datetime, timedelta
from collections import defaultdict
import qrcode
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
from config import config
from utils import XUIClient, generate_vless_link, setup_logging

setup_logging(config.logging)
logger = logging.getLogger(__name__)

bot = Bot(token=config.bot.token)
dp = Dispatcher()

xui_client = XUIClient(config)


class NewClientState(StatesGroup):
    waiting_for_comment = State()


class AddUserState(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_username = State()


# Антифлуд защита
user_message_count = defaultdict(list)
ANTIFLOOD_LIMIT = 5
ANTIFLOOD_TIME = 60
ANTIFLOOD_BLOCK_TIME = 300
flood_blocked_users = {}


def is_flood_blocked(user_id: int) -> bool:
    if user_id in flood_blocked_users:
        if datetime.now() < flood_blocked_users[user_id]:
            return True
        else:
            del flood_blocked_users[user_id]
    return False


def check_antiflood(user_id: int) -> bool:
    now = datetime.now()
    user_message_count[user_id] = [t for t in user_message_count[user_id] if
                                   now - t < timedelta(seconds=ANTIFLOOD_TIME)]
    user_message_count[user_id].append(now)
    if len(user_message_count[user_id]) > ANTIFLOOD_LIMIT:
        flood_blocked_users[user_id] = now + timedelta(seconds=ANTIFLOOD_BLOCK_TIME)
        user_message_count[user_id] = []
        return True
    return False


def is_admin(user_id):
    return user_id == config.users_db.get_main_admin()


def is_allowed(user_id):
    return config.users_db.is_allowed(user_id)


def is_blocked_by_admin(user_id):
    return config.users_db.is_blocked_by_admin(user_id)


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    # Отменяем ожидание комментария, если оно было
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer("✅ Создание ключа отменено.")

    # Проверка на блокировку администратором
    if is_blocked_by_admin(user_id):
        await message.answer("⛔ Вы заблокированы администратором.")
        return

    if not is_allowed(user_id):
        if is_flood_blocked(user_id):
            await message.answer("⛔ Вы временно заблокированы за флуд. Попробуйте позже.")
            return
        if check_antiflood(user_id):
            await message.answer(f"⚠️ Слишком много запросов! Заблокированы на {ANTIFLOOD_BLOCK_TIME // 60} минут.")
            return

    if is_allowed(user_id):
        if is_admin(user_id):
            await message.answer(
                f"👑 Администратор\n {username or first_name}\n\n"
                f"Команды:\n"
                f"/new - Создать ключ\n"
                f"/myclients - Мои ключи\n"
                f"/users - Список пользователей\n"
                f"/blockuser - Заблокировать пользователя\n"
                f"/unblockuser - Разблокировать пользователя\n"
                f"/removeuser - Удалить пользователя\n"
                f"/help - Помощь",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                f"👤 Пользователь\n {username or first_name}\n\n"
                f"Команды:\n"
                f"/new - Создать ключ\n"
                f"/myclients - Мои ключи\n"
                f"/help - Помощь",
                parse_mode="HTML"
            )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Запросить доступ", callback_data="request_access")]
        ])
        await message.answer(
            f"👋 Добро пожаловать, {first_name}!\n\n"
            f"Нажмите кнопку ниже, чтобы отправить запрос на доступ.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )


@dp.message(Command("new"))
async def cmd_new(message: Message, state: FSMContext):
    if not is_allowed(message.from_user.id):
        await message.answer("⛔ Доступ запрещен. Отправьте /start и запросите доступ у администратора.")
        return

    if is_blocked_by_admin(message.from_user.id):
        await message.answer("⛔ Вы заблокированы администратором.")
        return

    await message.answer(
        "⚠️ Внимание! Помните правило: Одно устройство - один ключ.\n\n"
        "📝 Введите комментарий к подключению (например: 'Для андроида', 'Для айфона', 'Для ноутбука' и т.д.):\n\n"
        "Это поможет вам ориентироваться в списке ключей. Вернуться в главное меню /start",
        parse_mode="HTML"
    )
    await state.set_state(NewClientState.waiting_for_comment)


@dp.message(NewClientState.waiting_for_comment)
async def process_new_comment(message: Message, state: FSMContext):
    comment = message.text.strip()

    # Проверка на недопустимые символы
    if comment.startswith('/'):
        await message.answer(
            "❌ Недопустимый символ! Комментарий не может начинаться с '/'. Пожалуйста, введите комментарий заново либо вернитесь в главное меню /start")
        return

    if len(comment) > 50:
        await message.answer("❌ Комментарий слишком длинный (максимум 50 символов). Попробуйте снова:")
        return

    await state.update_data(comment=comment)

    username = message.from_user.username
    if not username:
        username = message.from_user.first_name.lower().replace(" ", "_")

    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    email = f"{username}_{random_suffix}"

    status_msg = await message.answer(f"🔄 Ожидайте...")

    result = await xui_client.add_client(email, 0, 3650, comment)

    if result['success']:
        config.users_db.add_user_client(message.from_user.id, email, result['uuid'], comment)
        vless_link = generate_vless_link(result['uuid'], email, config.vpn, config.xui.inbound_id)

        qr = qrcode.QRCode(box_size=8, border=2)
        qr.add_data(vless_link)
        qr.make()
        qr_img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        qr_img.save(buffer, format="PNG")
        buffer.seek(0)

        await bot.delete_message(message.chat.id, status_msg.message_id)
        await message.answer_photo(
            photo=types.BufferedInputFile(buffer.getvalue(), filename="vless.png"),
            caption=f"\n\n📝 {comment}",
            parse_mode="HTML"
        )
        await message.answer(
            f"<code>{vless_link}</code>",
            parse_mode="HTML"
        )
    else:
        await status_msg.edit_text(f"❌ Ошибка: {result.get('error')}")

    await state.clear()


@dp.message(Command("myclients"))
async def cmd_my_clients(message: Message):
    if not is_allowed(message.from_user.id):
        await message.answer("⛔ Доступ запрещен.")
        return

    clients = config.users_db.get_user_clients(message.from_user.id)

    if not clients:
        await message.answer("📭 У вас пока нет ключей.\n\nИспользуйте /new для создания.")
        return

    buttons = []
    for client_id, email, uuid, comment, created_at in clients:
        display_text = comment if comment else email[:15]
        buttons.append([
            InlineKeyboardButton(text=f"🔑 {display_text}", callback_data=f"show_{client_id}")
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        f"📋 <b>Ваши ключи ({len(clients)})</b>\n\n"
        f"Выберите ключ для просмотра:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@dp.callback_query(lambda c: c.data and c.data.startswith('show_'))
async def show_client_details(callback_query: types.CallbackQuery):
    client_id = int(callback_query.data.split('_')[1])

    clients = config.users_db.get_user_clients(callback_query.from_user.id)
    client_data = None
    for c in clients:
        if c[0] == client_id:
            client_data = c
            break

    if not client_data:
        await callback_query.answer("Ключ не найден!", show_alert=True)
        return

    client_id, email, uuid, comment, created_at = client_data

    vless_link = generate_vless_link(uuid, email, config.vpn, config.xui.inbound_id)

    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(vless_link)
    qr.make()
    qr_img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    qr_img.save(buffer, format="PNG")
    buffer.seek(0)

    await callback_query.message.answer_photo(
        photo=types.BufferedInputFile(buffer.getvalue(), filename="vless.png"),
        caption=f"📝 <b>{comment if comment else 'Без комментария'}</b>\n\n"
                f"📅 Создано: {created_at[:16]}",
        parse_mode="HTML"
    )
    await callback_query.message.answer(
        f"<code>{vless_link}</code>",
        parse_mode="HTML"
    )
    await callback_query.answer()


@dp.message(Command("users"))
async def cmd_list_users(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Отказано в доступе.")
        return

    users = config.users_db.list_users()
    main_admin = config.users_db.get_main_admin()

    try:
        admin_chat = await bot.get_chat(main_admin)
        admin_name = f"@{admin_chat.username}" if admin_chat.username else str(main_admin)
    except:
        admin_name = str(main_admin)

    text = f"👑 <b>Администратор:</b> {admin_name}\n\n"

    if users:
        text += "<b>📋 Пользователи:</b>\n"
        for user_id, username, added_at in users:
            blocked_status = "🔒 Заблокирован" if config.users_db.is_blocked_by_admin(user_id) else "✅ Активен"
            if username:
                text += f"• @{username} (ID: {user_id}) - {blocked_status} - добавлен {added_at[:10]}\n"
            else:
                try:
                    chat = await bot.get_chat(user_id)
                    user_name = f"@{chat.username}" if chat.username else str(user_id)
                    text += f"• {user_name} - {blocked_status} - добавлен {added_at[:10]}\n"
                except:
                    text += f"• ID: {user_id} - {blocked_status} - добавлен {added_at[:10]}\n"
    else:
        text += "Нет добавленных пользователей."

    await message.answer(text, parse_mode="HTML")


@dp.message(Command("blockuser"))
async def cmd_block_user(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Отказано в доступе.")
        return

    users = config.users_db.list_users()
    if not users:
        await message.answer("📭 Список пользователей пуст.")
        return

    buttons = []
    for user_id, username, _ in users:
        if config.users_db.is_blocked_by_admin(user_id):
            continue
        if username:
            button_text = f"@{username}"
        else:
            try:
                chat = await bot.get_chat(user_id)
                button_text = f"@{chat.username}" if chat.username else str(user_id)
            except:
                button_text = str(user_id)
        buttons.append([InlineKeyboardButton(text=f"🔒 {button_text}", callback_data=f"block_{user_id}")])

    if not buttons:
        await message.answer("📭 Нет активных пользователей для блокировки.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("👥 Выберите пользователя для блокировки:", reply_markup=keyboard)


@dp.message(Command("unblockuser"))
async def cmd_unblock_user(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Отказано в доступе.")
        return

    # Получаем всех заблокированных пользователей
    with sqlite3.connect(config.users_db.db_path) as conn:
        cursor = conn.execute("SELECT user_id FROM blocked_users")
        blocked_ids = [row[0] for row in cursor.fetchall()]

    if not blocked_ids:
        await message.answer("📭 Нет заблокированных пользователей.")
        return

    buttons = []
    for user_id in blocked_ids:
        try:
            chat = await bot.get_chat(user_id)
            button_text = f"@{chat.username}" if chat.username else str(user_id)
        except:
            button_text = str(user_id)
        buttons.append([InlineKeyboardButton(text=f"🔓 {button_text}", callback_data=f"unblock_{user_id}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("👥 Выберите пользователя для разблокировки:", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data and c.data.startswith('block_'))
async def process_block_user(callback_query: types.CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔ Отказано в доступе", show_alert=True)
        return

    user_id = int(callback_query.data.split('_')[1])

    if config.users_db.block_user(user_id, callback_query.from_user.id):
        await callback_query.message.edit_text(f"✅ Пользователь заблокирован.")
        try:
            await bot.send_message(user_id, "⛔ Вы заблокированы администратором.")
        except:
            pass
    else:
        await callback_query.message.edit_text("❌ Ошибка при блокировке!")
    await callback_query.answer()


@dp.callback_query(lambda c: c.data and c.data.startswith('unblock_'))
async def process_unblock_user(callback_query: types.CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔ Отказано в доступе", show_alert=True)
        return

    user_id = int(callback_query.data.split('_')[1])

    if config.users_db.unblock_user(user_id):
        await callback_query.message.edit_text(f"✅ Пользователь разблокирован.")
        try:
            await bot.send_message(user_id, "✅ Вы разблокированы администратором.")
        except:
            pass
    else:
        await callback_query.message.edit_text("❌ Ошибка при разблокировке!")
    await callback_query.answer()


@dp.message(Command("removeuser"))
async def cmd_remove_user(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Отказано в доступе.")
        return

    users = config.users_db.list_users()
    if not users:
        await message.answer("📭 Список пользователей пуст.")
        return

    buttons = []
    for user_id, username, _ in users:
        if username:
            button_text = f"@{username}"
        else:
            try:
                chat = await bot.get_chat(user_id)
                button_text = f"@{chat.username}" if chat.username else str(user_id)
            except:
                button_text = str(user_id)
        buttons.append([InlineKeyboardButton(text=button_text, callback_data=f"remove_{user_id}")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("👥 Выберите пользователя для удаления:", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data and c.data.startswith('remove_'))
async def process_remove_user(callback_query: types.CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔ Отказано в доступе", show_alert=True)
        return

    user_id = int(callback_query.data.split('_')[1])

    if user_id == config.users_db.get_main_admin():
        await callback_query.answer("❌ Нельзя удалить главного администратора!", show_alert=True)
        return

    try:
        chat = await bot.get_chat(user_id)
        user_name = f"@{chat.username}" if chat.username else str(user_id)
    except:
        user_name = str(user_id)

    if config.users_db.remove_user(user_id):
        await callback_query.message.edit_text(f"✅ Пользователь {user_name} удален.")
        try:
            await bot.send_message(user_id, "⛔ Ваш доступ отозван администратором.")
        except:
            pass
    else:
        await callback_query.message.edit_text("❌ Ошибка при удалении!")
    await callback_query.answer()


@dp.message(Command("help"))
async def cmd_help(message: Message):
    if not is_allowed(message.from_user.id):
        await message.answer("⛔ Доступ запрещен. Отправьте /start для запроса доступа.")
        return

    if is_admin(message.from_user.id):
        text = """
<b>👑 Команды администратора:</b>

/new - Создать ключ
/myclients - Мои ключи
/users - Список пользователей
/blockuser - Заблокировать пользователя
/unblockuser - Разблокировать пользователя
/removeuser - Удалить пользователя
/help - Помощь

<i>Пользователи сами отправляют запрос на доступ через /start</i>
"""
    else:
        text = """
⚠️ Внимание! Помните правило: Одно устройство - один ключ.      

<b>📖 Команды пользователя:</b>

/new - Создать ключ
/myclients - Мои ключи
/help - Помощь

<i>Если у вас нет доступа - отправьте /start и нажмите "Запросить доступ"</i>
"""
    await message.answer(text, parse_mode="HTML")


@dp.callback_query(lambda c: c.data == "request_access")
async def process_request_access(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username
    first_name = callback_query.from_user.first_name
    last_name = callback_query.from_user.last_name

    if is_allowed(user_id):
        await callback_query.message.edit_text("✅ У вас уже есть доступ! Используйте /start")
        await callback_query.answer()
        return

    admin_id = config.users_db.get_main_admin()
    user_info = f"@{username}" if username else first_name
    user_full_name = f"{first_name} {last_name if last_name else ''}".strip()

    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Разрешить", callback_data=f"approve_{user_id}"),
         InlineKeyboardButton(text="❌ Заблокировать", callback_data=f"deny_{user_id}")]
    ])

    await bot.send_message(
        admin_id,
        f"🆕 <b>Новый запрос на доступ!</b>\n\n"
        f"👤 Пользователь: {user_info}\n"
        f"📝 Имя: {user_full_name}\n"
        f"🆔 ID: <code>{user_id}</code>",
        reply_markup=admin_keyboard,
        parse_mode="HTML"
    )

    await callback_query.message.edit_text("📨 Запрос отправлен! Ожидайте")
    await callback_query.answer()


@dp.callback_query(lambda c: c.data and c.data.startswith(('approve_', 'deny_')))
async def process_admin_decision(callback_query: types.CallbackQuery):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔ Отказано в доступе", show_alert=True)
        return

    action, user_id_str = callback_query.data.split('_')
    user_id = int(user_id_str)

    try:
        chat = await bot.get_chat(user_id)
        username = chat.username
        first_name = chat.first_name
        user_info = f"@{username}" if username else first_name
    except:
        user_info = str(user_id)

    if action == "approve":
        if config.users_db.add_user(user_id, username, callback_query.from_user.id):
            await callback_query.message.edit_text(f"✅ Пользователь {user_info} добавлен!")
            try:
                await bot.send_message(user_id, "🚀 Доступ разрешен! Отправьте /start для начала работы.")
            except:
                pass
        else:
            await callback_query.message.edit_text(f"❌ Ошибка при добавлении пользователя!")
    else:
        await callback_query.message.edit_text(f"❌ Пользователь {user_info} заблокирован.")
        config.users_db.block_user(user_id, callback_query.from_user.id)
        try:
            await bot.send_message(user_id, "❌ Ваш запрос на доступ отклонен администратором.")
        except:
            pass
    await callback_query.answer()


@dp.message()
async def handle_unknown(message: Message):
    user_id = message.from_user.id

    if is_blocked_by_admin(user_id):
        await message.answer("⛔ Вы заблокированы администратором.")
        return

    if is_flood_blocked(user_id):
        await message.answer("⛔ Вы временно заблокированы за флуд. Попробуйте позже.")
        return

    if not is_allowed(user_id):
        if check_antiflood(user_id):
            await message.answer(
                f"⚠️ Вы отправляете слишком много сообщений!\n\nЗаблокированы на {ANTIFLOOD_BLOCK_TIME // 60} минут.")
            logger.warning(f"Пользователь {user_id} заблокирован за флуд")
            return

    if message.text and message.text.startswith('/'):
        return

    if is_allowed(user_id):
        await message.answer(
            "❓ Неизвестная команда.\n\nОтправьте /help для списка команд.",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❓ Для начала работы отправьте /start",
            parse_mode="HTML"
        )


async def main():
    logger.info("🚀 Запуск бота...")
    logger.info(f"👑 Администратор: {config.users_db.get_main_admin()}")

    if await xui_client.login():
        logger.info("✅ Подключение к X-UI установлено")
        await dp.start_polling(bot)
    else:
        logger.error("❌ Не удалось подключиться к X-UI")
        return


if __name__ == "__main__":
    asyncio.run(main())
