# bot.py
# Главный файл бота. Запуск: python bot.py
# Библиотека: aiogram 3.x

import asyncio
import time
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import config
import database

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# ---------- Защита от спама (простой rate limit) ----------
# Храним время последнего сообщения от каждого пользователя
last_message_time = {}
RATE_LIMIT_SECONDS = 2  # не чаще 1 сообщения в 2 секунды


def is_rate_limited(user_id: int) -> bool:
    now = time.time()
    last = last_message_time.get(user_id, 0)
    if now - last < RATE_LIMIT_SECONDS:
        return True
    last_message_time[user_id] = now
    return False


# ---------- FSM (состояния) для сбора обращения ----------
class SupportForm(StatesGroup):
    choosing_category = State()
    entering_order_number = State()
    entering_message = State()


# ---------- FAQ: тексты ответов на частые вопросы ----------
FAQ = {
    "faq_delivery": (
        "📦 *Доставка*\n\n"
        "Мы отправляем заказы в течение 1-2 рабочих дней после оплаты.\n"
        "Срок доставки зависит от региона и обычно составляет 3-7 дней."
    ),
    "faq_payment": (
        "💳 *Оплата*\n\n"
        "Доступна оплата картой онлайн, а также через СБП.\n"
        "Оплата производится сразу при оформлении заказа на сайте."
    ),
    "faq_sizes": (
        "📐 *Размеры наборов*\n\n"
        "Наборы доступны в размере A4 и открытки формата 10х10см.\n"
    ),
    "faq_track": (
        "🚚 *Где мой заказ?*\n\n"
        "Трек-номер отправляется на вашу почту после отправки заказа.\n"
        "Если письмо не пришло в течение 3 дней — напишите нам в поддержку, укажите номер заказа."
    ),
}


# ---------- Главное меню ----------
def main_menu_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Частые вопросы", callback_data="menu_faq")],
        [InlineKeyboardButton(text="✍️ Написать в поддержку", callback_data="menu_support")],
        [InlineKeyboardButton(text="🌐 Перейти на сайт", url=config.SHOP_URL)],
    ])
    return kb


def faq_menu_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Доставка", callback_data="faq_delivery")],
        [InlineKeyboardButton(text="💳 Оплата", callback_data="faq_payment")],
        [InlineKeyboardButton(text="📐 Размеры наборов", callback_data="faq_sizes")],
        [InlineKeyboardButton(text="🚚 Где мой заказ?", callback_data="faq_track")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_back")],
    ])
    return kb


def support_category_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Вопрос по заказу", callback_data="cat_order")],
        [InlineKeyboardButton(text="💡 Предложение", callback_data="cat_suggestion")],
        [InlineKeyboardButton(text="⚠️ Проблема с товаром", callback_data="cat_problem")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_back")],
    ])
    return kb


CATEGORY_NAMES = {
    "cat_order": "Вопрос по заказу",
    "cat_suggestion": "Предложение",
    "cat_problem": "Проблема с товаром",
}


# ---------- Хендлеры ----------

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Здравствуйте! 🌸\n\n"
        f"Это бот поддержки магазина «{config.SHOP_NAME}».\n"
        f"Выберите, что вас интересует:",
        reply_markup=main_menu_kb()
    )


@router.callback_query(F.data == "menu_back")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        f"Главное меню «{config.SHOP_NAME}»:",
        reply_markup=main_menu_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "menu_faq")
async def show_faq(callback: CallbackQuery):
    await callback.message.edit_text("Выберите вопрос:", reply_markup=faq_menu_kb())
    await callback.answer()


@router.callback_query(F.data.in_(FAQ.keys()))
async def answer_faq(callback: CallbackQuery):
    text = FAQ[callback.data]
    await callback.message.edit_text(text, reply_markup=faq_menu_kb(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "menu_support")
async def start_support(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SupportForm.choosing_category)
    await callback.message.edit_text(
        "С чем связано ваше обращение?",
        reply_markup=support_category_kb()
    )
    await callback.answer()


@router.callback_query(SupportForm.choosing_category, F.data.in_(CATEGORY_NAMES.keys()))
async def category_chosen(callback: CallbackQuery, state: FSMContext):
    await state.update_data(category=CATEGORY_NAMES[callback.data])

    if callback.data == "cat_order" or callback.data == "cat_problem":
        # Для этих категорий полезно спросить номер заказа
        await state.set_state(SupportForm.entering_order_number)
        await callback.message.edit_text(
            "Укажите номер вашего заказа (или отправьте «-», если не знаете):"
        )
    else:
        await state.update_data(order_number="—")
        await state.set_state(SupportForm.entering_message)
        await callback.message.edit_text(
            "Опишите ваше предложение одним сообщением:"
        )
    await callback.answer()


@router.message(SupportForm.entering_order_number)
async def order_number_entered(message: Message, state: FSMContext):
    await state.update_data(order_number=message.text)
    await state.set_state(SupportForm.entering_message)
    await message.answer("Спасибо! Теперь опишите проблему или вопрос одним сообщением:")


@router.message(SupportForm.entering_message)
async def message_entered(message: Message, state: FSMContext):
    if is_rate_limited(message.from_user.id):
        await message.answer("Пожалуйста, подождите пару секунд перед отправкой следующего сообщения.")
        return

    data = await state.get_data()
    category = data.get("category", "Не указано")
    order_number = data.get("order_number", "—")

    ticket_id = database.add_ticket(
        user_id=message.from_user.id,
        username=message.from_user.username or message.from_user.full_name,
        category=category,
        order_number=order_number,
        message=message.text
    )

    # Пересылаем обращение в админ-чат
    admin_text = (
        f"🆕 *Новое обращение #{ticket_id}*\n\n"
        f"👤 Пользователь: @{message.from_user.username or '—'} (id: {message.from_user.id})\n"
        f"📂 Категория: {category}\n"
        f"🔢 Номер заказа: {order_number}\n\n"
        f"💬 Сообщение:\n{message.text}\n\n"
        f"Чтобы ответить клиенту, используйте:\n`/reply {ticket_id} ваш текст ответа`"
    )
    await bot.send_message(config.ADMIN_CHAT_ID, admin_text, parse_mode="Markdown")

    await message.answer(
        f"✅ Спасибо! Ваше обращение принято.\n"
        f"Мы ответим вам в ближайшее время.",
        reply_markup=main_menu_kb()
    )
    await state.clear()


# ---------- Ответ администратора клиенту ----------
@router.message(Command("reply"))
async def admin_reply(message: Message):
    # Работает только если команда пришла из админ-чата
    if message.chat.id != config.ADMIN_CHAT_ID:
        return

    try:
        # Формат: /reply 5 Ваш заказ отправлен сегодня
        parts = message.text.split(maxsplit=2)
        ticket_id = int(parts[1])
        reply_text = parts[2]
    except (IndexError, ValueError):
        await message.answer("Использование: /reply <номер_обращения> <текст ответа>")
        return

    # Находим user_id по номеру тикета напрямую в БД
    import sqlite3
    conn = sqlite3.connect(database.DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM tickets WHERE id=?", (ticket_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        await message.answer(f"Обращение #{ticket_id} не найдено.")
        return

    target_user_id = row[0]

    await bot.send_message(
        target_user_id,
        f"💬 Ответ от поддержки по обращению #{ticket_id}:\n\n{reply_text}"
    )
    database.close_ticket(ticket_id)
    await message.answer(f"✅ Ответ отправлен клиенту, обращение #{ticket_id} закрыто.")


@router.message(Command("open_tickets"))
async def list_open_tickets(message: Message):
    if message.chat.id != config.ADMIN_CHAT_ID:
        return

    tickets = database.get_open_tickets()
    if not tickets:
        await message.answer("Открытых обращений нет.")
        return

    text = "📋 *Открытые обращения:*\n\n"
    for t in tickets:
        ticket_id, username, category, order_number, msg, created_at = t
        text += f"#{ticket_id} | @{username} | {category} | заказ: {order_number}\n{msg[:80]}\n\n"

    await message.answer(text, parse_mode="Markdown")


# ---------- Запуск ----------
async def main():
    database.init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
