import telebot
from config import TOKEN
from telebot import types
from question import * 

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton('FAQ', callback_data='questions'),
        types.InlineKeyboardButton('Связь с специалистом', callback_data='link')
    )

    bot.send_message(message.chat.id, 'Вас приветствует команда "Продаем всё на свете"! Здесь вы можете задать любой интересующий вас вопрос, мы сразу ответим.', kb)
