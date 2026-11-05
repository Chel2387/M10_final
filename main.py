import logging
import traceback
import telebot
from telebot import types
from FAQ import FAQ
from config import ADMIN_IDS, TOKEN
from date_base import get_request, init_db, list_requests, set_status

logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot(TOKEN)

SPECIALIST_UNAVAILABLE = "Этот раздел в разработке, приносим свои извинения"

FAQ_BUTTONS = [
    "Оформить заказ",
    "Статус заказа",
    "Отменить заказ",
    "Товар повреждён",
    "Связь с поддержкой",
    "Информация о доставке",
]


class PrintExceptions(telebot.ExceptionHandler):
    def handle(self, exception):
        traceback.print_exc()
        return True


bot.exception_handler = PrintExceptions()


def is_admin(user_id):
    return user_id in ADMIN_IDS


def main_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton("Часто задаваемые вопросы", callback_data="faq"))
    keyboard.row(types.InlineKeyboardButton("Написать свой вопрос", callback_data="ask"))
    keyboard.row(types.InlineKeyboardButton("Связаться со специалистом", callback_data="specialist"))
    return keyboard


def faq_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    for index, title in enumerate(FAQ_BUTTONS):
        keyboard.row(types.InlineKeyboardButton(title, callback_data=f"faq:{index}"))
    keyboard.row(types.InlineKeyboardButton("В меню", callback_data="menu"))
    return keyboard


def after_answer_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(types.InlineKeyboardButton("Другие вопросы", callback_data="faq"))
    keyboard.row(types.InlineKeyboardButton("Нужен специалист", callback_data="specialist"))
    keyboard.row(types.InlineKeyboardButton("В меню", callback_data="menu"))
    return keyboard


def welcome_text():
    return (
        "Добро пожаловать в поддержку магазина «Продаем всё на свете»!\n\n"
        "Мы поможем быстро:\n"
        "• ответим на частые вопросы;\n"
        "• подскажем, что делать с заказом и доставкой.\n\n"
        "Напишите вопрос текстом или выберите действие ниже."
    )


def safe_send(chat_id, text, reply_markup=None):
    try:
        return bot.send_message(chat_id, text, reply_markup=reply_markup)
    except Exception:
        traceback.print_exc()
        return bot.send_message(chat_id, text)


def send_menu(chat_id, text=None):
    safe_send(chat_id, text or welcome_text(), main_keyboard())


def send_specialist_stub(chat_id):
    safe_send(chat_id, SPECIALIST_UNAVAILABLE, main_keyboard())


def handle_user_question(message, text):
    chat_id = message.chat.id
    matches = match_faq(text)
    if matches and matches[0][2] >= 0.55:
        safe_send(
            chat_id,
            "Нашла ответ в базе вопросов:\n\n" + format_matches(matches),
            after_answer_keyboard(),
        )
        return

    send_specialist_stub(chat_id)


@bot.message_handler(commands=["start", "help", "menu"])
def start(message):
    send_menu(message.chat.id)


@bot.message_handler(commands=["tickets", "admin"])
def tickets(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "Эта команда доступна только администраторам.")
        return

    parts = message.text.split()
    status = parts[1] if len(parts) > 1 else "open"
    if status not in {"open", "closed", "all"}:
        bot.send_message(message.chat.id, "Используйте: /tickets open | closed | all")
        return

    rows = list_requests(status=None if status == "all" else status)
    if not rows:
        bot.send_message(message.chat.id, "Заявок пока нет.")
        return

    lines = ["Заявки специалистам:\n"]
    for row in rows:
        preview = (row["message"] or "").replace("\n", " ")
        if len(preview) > 80:
            preview = preview[:77] + "..."
        lines.append(
            f"№{row['id']} [{row['status']}] id {row['user_id']}\n"
            f"{row['created_at']}\n"
            f"{preview}\n"
        )
    lines.append("Закрыть заявку: /close 12")
    bot.send_message(message.chat.id, "\n".join(lines))


@bot.message_handler(commands=["close"])
def close_ticket(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "Эта команда доступна только администраторам.")
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.send_message(message.chat.id, "Укажите номер заявки: /close 12")
        return

    request_id = int(parts[1])
    ticket = get_request(request_id)
    if not ticket:
        bot.send_message(message.chat.id, "Заявка с таким номером не найдена.")
        return

    set_status(request_id, "closed")
    bot.send_message(message.chat.id, f"Заявка №{request_id} закрыта.")
    try:
        bot.send_message(
            ticket["user_id"],
            f"Ваша заявка №{request_id} закрыта специалистом. Если вопрос остался — напишите нам снова.",
        )
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    chat_id = call.message.chat.id if call.message else call.from_user.id
    data = call.data or ""
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    if data == "menu":
        send_menu(chat_id)
        return

    if data == "faq":
        safe_send(chat_id, "Выберите вопрос — отвечу сразу:", faq_keyboard())
        return

    if data == "ask":
        bot.send_message(chat_id, "Напишите вопрос своими словами. Попробую найти ответ в FAQ.")
        return

    if data == "specialist":
        send_specialist_stub(chat_id)
        return

    if data.startswith("faq:"):
        try:
            index = int(data.split(":")[1])
            question = list(FAQ.keys())[index]
        except (ValueError, IndexError):
            send_menu(chat_id, "Этот вопрос уже недоступен. Выберите другой в меню.")
            return
        safe_send(chat_id, f"{question}\n{FAQ[question]}", after_answer_keyboard())


@bot.message_handler(content_types=["text"])
def text_message(message):
    handle_user_question(message, message.text)


if __name__ == "__main__":
    init_db()
    bot.remove_webhook()
    print("Бот поддержки запущен")
    bot.infinity_polling(skip_pending=True)
