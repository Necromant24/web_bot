import config
import telebot

# Telegram bot
bot = telebot.TeleBot(config.tg_token, skip_pending=True)


def send_msg_to_tg(message_data):
    bot.send_message(config.group_id, message_data)


def get_email_from_message(message):
    lines = message.split('\n')
    email = ""
    for line in lines:
        if line.startswith("email:"):
            email = line.split(":")[1].strip()
            break

    return email


def replace_endl(text):
    return text.replace('\n', "")
