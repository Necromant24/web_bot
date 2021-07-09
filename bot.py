import config
import messages
import telebot
from telebot import types
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard
from pymessenger import Button
from pymessenger.bot import Bot
import gspread
import requests
import json
import datetime
import re
import time
import random
import sys
import os
import threading
import sqlite3 as sql
from flask import Flask, request


# ░█████╗░░█████╗░███╗░░░███╗███╗░░░███╗░█████╗░███╗░░██╗
# ██╔══██╗██╔══██╗████╗░████║████╗░████║██╔══██╗████╗░██║
# ██║░░╚═╝██║░░██║██╔████╔██║██╔████╔██║██║░░██║██╔██╗██║
# ██║░░██╗██║░░██║██║╚██╔╝██║██║╚██╔╝██║██║░░██║██║╚████║
# ╚█████╔╝╚█████╔╝██║░╚═╝░██║██║░╚═╝░██║╚█████╔╝██║░╚███║
# ░╚════╝░░╚════╝░╚═╝░░░░░╚═╝╚═╝░░░░░╚═╝░╚════╝░╚═╝░░╚══╝


def db_find_value(col_name, value):
    """ Check if value exists in database and return corresponding row, 'col_name' must be name of DB column
        DB columns in order: email, date, tariff, sub, tg_id, vk_id, fb_id, state, rate, review_time, received, verified """

    with sql.connect(config.db_file) as con:
        cur = con.cursor()
        #test code
        some = cur.execute("SELECT 1;").fetchall()
        all_data = cur.execute("SELECT * FROM clients;").fetchall()

        cur.execute(f"SELECT * FROM clients WHERE {col_name} = ?", (str(value).lower(),))
        res[:] = cur.fetchall()

        if res:
            return res[0]

        return 0



# --------------------------------------------------
def client_info_msg(col_name, value):
    """ Make a message with client tariff info """

    info = db_find_value(col_name, value)
    if not info:
        return "No info about client"

    message = f"\U00002139\nemail: {info[0]}\n" \
              f"date: {info[1]}\n" \
              f"tariff: {info[2]}\n" \
              f"sub: {info[3]}\n"

    return message


# -------------------------------------------------
def update_pinned_bottom(emails_list):
    """ Update bottom part of pinned message that contains emails of clients who were reminded about expiring tariff """

    # Pinned message text is stored in file
    with open("pinned.txt", "r+") as file:
        top = file.read().split("==========")[0]
        bottom = emails_list
        new_full = top + "==========\n" + bottom

    with open("pinned.txt", "w") as file:
        file.write(new_full)

    bot.edit_message_text(new_full, config.group_id, config.pinned_msg, parse_mode='HTML')


# --------------------------------------------------
def info_too_soon(id):
    """ Check if previous client info message was less than 5 minutes ago """

    previous = clients_info_time.get(id) or 0
    time_past = int(time.time() - previous)

    if time_past < 300:
        return True
    else:
        clients_info_time[id] = time.time()
        return False


# --------------------------------------------------
def update_clients(search_pair, *change_pairs):
    """ Update local database with new relation
        Search_pair and change_pairs args must be [DB column, value] pairs and be even length
        DB columns in order: email, date, tariff, sub, tg_id, vk_id, fb_id, state, rate, review_time, received, verified """

    with sql.connect(config.db_file) as con:

        # Example: "tg_id = '123', vk_id = '456', fb_id = '789'"
        pairs = ", ".join([f"{i[0]} = '{i[1]}'" for i in change_pairs])

        cur = con.cursor()
        cur.execute(f"UPDATE clients SET {pairs} WHERE {search_pair[0]} = '{search_pair[1]}'")
        con.commit()


# --------------------------------------------------
def get_info(wanted_col, search_col, search_val):
    """ Find some column value by other corresponding column value """

    with sql.connect(config.db_file) as con:
        cur = con.cursor()
        cur.execute(f"SELECT {wanted_col} FROM clients WHERE {search_col} = '{search_val}'")
        info[:] = cur.fetchall()

        if info:
            return info[0][0]

        return 0


# --------------------------------------------------
def new_client(email, type_id, id):
    """ Add new row in database. For users who have specified mail that is not in the database """

    client = [email.lower(), "-", "-", "-", "0", "0", "0", "CLOSED", "0", "0", "NO", 0]

    if type_id == "tg_id":
        client[4] = id
    elif type_id == "vk_id":
        client[5] = id
    elif type_id == "fb_id":
        client[6] = id

    with sql.connect(config.db_file) as con:
        cur = con.cursor()
        cur.execute(f"INSERT INTO clients VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", client)

        con.commit()


# -------------------------------------------------
def delete_client(search_col, search_val):
    """ Delete row from DB (if only single row was found) """

    with sql.connect("test.db") as con:
        cur = con.cursor()
        cur.execute(f"SELECT * FROM clients WHERE {search_col} = ?", (search_val,))

        if len(cur.fetchall()) > 1:
            return f"В базе несколько значений с {search_col} = {search_val}! Отмена"

        cur.execute(f"DELETE FROM clients WHERE {search_col} = ?", (search_val,))
        con.commit()
        return f"Запись с {search_col} = {search_val} удалена\n"


# --------------------------------------------------
def open_dialogue(type_id, id, state="OPEN"):
    """ Change client state in DB to OPEN (or other) and update pinned message with new info"""

    update_clients([type_id, id], ["state", state])
    #update_pinned_top()


def write_payment(email, amount):
    """ Write payment info in .csv file """

    with open(config.base_file, 'a+') as file:
        file.write(f"{email};;;{amount}\n")


# --------------------------------------------------
def log_report(message, error):
    """ Write error info in log file """

    line_number = sys.exc_info()[2].tb_lineno

    with open('log.txt', 'a+') as log:
        log.write(f"{datetime.datetime.today()}\n{message}\n"
                  f"Line {line_number}\n{error}\n##################################\n\n")


# ████████╗███████╗██╗░░░░░███████╗░██████╗░██████╗░░█████╗░███╗░░░███╗
# ╚══██╔══╝██╔════╝██║░░░░░██╔════╝██╔════╝░██╔══██╗██╔══██╗████╗░████║
# ░░░██║░░░█████╗░░██║░░░░░█████╗░░██║░░██╗░██████╔╝███████║██╔████╔██║
# ░░░██║░░░██╔══╝░░██║░░░░░██╔══╝░░██║░░╚██╗██╔══██╗██╔══██║██║╚██╔╝██║
# ░░░██║░░░███████╗███████╗███████╗╚██████╔╝██║░░██║██║░░██║██║░╚═╝░██║
# ░░░╚═╝░░░╚══════╝╚══════╝╚══════╝░╚═════╝░╚═╝░░╚═╝╚═╝░░╚═╝╚═╝░░░░░╚═╝


def telegram():
    """ Handles all telegram messages, makes mailing. Checks for user ID in database.
        If ID found - forward message to support group, otherwise ask sender for registration email.
        Also provides possibility to edit database, sending special commands directly to bot """

    print("\nTelegram running")

    def tg_to_tg(to_id, message, from_support=False, review=False):
        """ Transfers messages from client to support and back
            Used instead of TG API forward_message method to be able to reply every client, even those who restricted forwarding """

        text = message.text or message.caption or ''

        # Add info about client to message
        if not from_support:

            # Upper part of the message with emoji and name
            header = f"\U0001F4E2 Отзыв\n" if review \
                else f"\U0001F4AC{message.from_user.first_name} {message.from_user.last_name}\n"

            # Bottom part of the message with id and social network name, so we can reply back
            check = "\U00002705" if get_info("verified", "tg_id", message.chat.id) else ''
            bottom = f"{message.chat.id} Telegram{check}"

            text = header + text + "\n\n"

            # Add client tariff info
            if not info_too_soon(message.chat.id):
                text += "\n" + client_info_msg("tg_id", message.chat.id)

            text += bottom

        if message.text:
            bot.send_message(to_id, text)
        if message.photo:
            photo_max_res = sorted(message.photo, key=lambda x: x.height)[-1].file_id
            bot.send_photo(to_id, photo_max_res, caption=text)
        if message.video:
            bot.send_video(to_id, message.video.file_id, caption=text)
        if message.document:
            bot.send_document(to_id, message.document.file_id, caption=text)
        if message.voice:
            bot.send_voice(to_id, message.voice.file_id)

            # Voice message has no caption, so send empty text message with top+bottom borders to be able to reply
            # Same for audio and stickers
            if not from_support:
                bot.send_message(to_id, text)

        if message.audio:
            bot.send_audio(to_id, message.audio.file_id)

            if not from_support:
                bot.send_message(to_id, text)

        if message.sticker:
            bot.send_sticker(to_id, message.sticker.file_id)

            if not from_support:
                bot.send_message(to_id, text)

    def save_file(message, folder=config.files_path, check=False):
        """ Save attachment from message to local folder and return its path """

        if message.photo:
            file_id = message.photo[-1].file_id
            file_name = bot.get_file_url(file_id).split('/')[-1]
            a = bot.get_file(file_id)
            downloaded_file = bot.download_file(a.file_path)
            path = os.path.join(folder, file_name)

            if check and file_name in os.listdir(config.pay_imgs_path):
                return "File already in folder"

            with open(path, "wb") as new_file:
                new_file.write(downloaded_file)

        elif message.document:
            name = message.document.file_name
            a = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(a.file_path)
            path = folder + name
            with open(path, "wb") as new_file:
                new_file.write(downloaded_file)

        return path

    def check_mail_edit(message):
        """ Check if message fits options for DB editing commands """

        # Check if message is sent by bot owner
        user_check = message.from_user.id in [config.my_id, config.owner_id]

        if user_check and message.text == "/почта":
            return True

        # Every message except starting ('/почта') must be reply to bot message
        if not message.reply_to_message or not message.reply_to_message.text:
            return False

        reply_text = message.reply_to_message.text

        # Check if reply message sender is bot
        bot_check = message.reply_to_message.from_user.id == config.bot_id

        # Check if reply message text is special text that bot sends to owner
        text_check = reply_text in [messages.edit_wrong_mail, messages.edit_true_mail, messages.edit_confirm]

        return user_check and bot_check and text_check

    # --------------------------------------------------
    def check_mailing(message):
        """ Check if message fits options for mailing commands """

        # Check if message is sent by bot owner
        user_check = message.from_user.id in [config.my_id, config.owner_id]
        txt = message.text or message.caption

        if user_check and txt == "/рассылка":
            return True

        # Every message except starting ('/рассылка') must be reply to bot message
        if not message.reply_to_message or not message.reply_to_message.text:
            return False

        reply_text = message.reply_to_message.text

        # Check if reply message sender is bot
        bot_check = message.reply_to_message.from_user.id == config.bot_id

        # Check if reply message text is special text that bot sends to owner
        text_check = reply_text in [messages.mailing_tariffs, messages.mailing_message] \
                    or reply_text.startswith("Следующие тарифы:")
        return user_check and bot_check and text_check

    # --------------------------------------------------
    #test code - changed urgent to true
    def support(message, urgent=True):
        """ Handles every attempt to open support dialogue. Do not open if not urgent and not in working time """

        buttons = types.InlineKeyboardMarkup()

        # User trying to contact support in non working time
        if not urgent:
            if not 17 <= datetime.datetime.today().hour < 22 or datetime.datetime.today().isoweekday() in [6, 7]:
                buttons.add(types.InlineKeyboardButton(text="Срочная связь", callback_data="urgent"))
                bot.send_message(message.chat.id, messages.non_working, reply_markup=buttons)

                return

        open_dialogue("tg_id", message.chat.id)

        buttons = types.InlineKeyboardMarkup()
        buttons.add(types.InlineKeyboardButton(text="Первичная настройка", callback_data="install"))
        buttons.add(types.InlineKeyboardButton(text="Другое", callback_data="other"))
        buttons.add(types.InlineKeyboardButton(text="ZGC SHOP", callback_data="market"))

        # Ask user to choose problem type
        msg = messages.type_support
        sub = get_info("sub", "tg_id", message.chat.id)
        if sub != '-' and int(get_info("verified", "tg_id", message.chat.id)):
            msg += f"\U000026A1 Ваша подписка: {sub}"
        bot.send_message(message.chat.id, msg, reply_markup=buttons)

    # --------------------------------------------------
    def initial_buttons(message, send_text=messages.buttons_menu):
        """ Send user message with default reply keyboard"""

        markup_buttons = types.ReplyKeyboardMarkup(resize_keyboard=True)
        item_pay = types.InlineKeyboardButton("\U0001F4B4 Оплата")
        item_shop = types.InlineKeyboardButton("\U0001F6D2 ZGC SHOP")
        item_trial = types.InlineKeyboardButton("\U0001F193 Пробный период")
        item_promo = types.InlineKeyboardButton("\U0001F4F0 Узнать больше")
        item_turk = types.InlineKeyboardButton("\U0001F1F9\U0001F1F2Для Туркменистана")
        item_coop = types.InlineKeyboardButton("\U0001F91D Сотрудничество")
        item_connection = types.InlineKeyboardButton("\U00002753 Связаться с поддержкой")
        markup_buttons.add(item_pay, item_trial, item_turk, item_promo,
                           item_shop, item_coop, item_connection)

        bot.send_message(message.chat.id, send_text,
                         reply_markup=markup_buttons)


    @bot.message_handler(commands=["start"])
    def start(message):
        """ Ask user to send his email address if not identified. Otherwise send default message with reply keyboard """

        #test code
        finded_val = db_find_value("tg_id", message.chat.id)


        if not db_find_value("tg_id", message.chat.id):
            bot.send_message(message.chat.id, messages.send_email)
        else:
            initial_buttons(message)

    @bot.message_handler(func=lambda message: message.chat.id != config.group_id and
                                              not db_find_value("tg_id", message.chat.id),
                         content_types=['text', 'photo', 'video', 'voice', 'audio', 'sticker', 'document'])
    def unknown_user(message):
        """ Handle all messages if user is not identified """

        # Check if message text has '@' between some non-space symbols
        if not message.text or not re.findall(r"\S+@\S+", message.text):
            bot.send_message(message.chat.id, messages.send_email)
            return

        email = re.findall(r"\S+@\S+", message.text)[0].lower()
        # Suppose user entered email, look for it in database
        email_info = db_find_value("email", email)

        # Email not found, insert new row in DB with that email and user ID
        if not email_info:
            new_client(email, "tg_id", message.chat.id)
            initial_buttons(message)

        # Email is already used by user with other ID, ask to immediately contact us
        elif email_info[4] != "0":
            new_client("-", "tg_id", message.chat.id)
            open_dialogue("tg_id", message.chat.id)
            initial_buttons(message, messages.email_already_used)

        # Email found in DB and not used by other ID, update DB
        else:
            update_clients(["email", email], ["tg_id", message.chat.id])
            initial_buttons(message)

    @bot.message_handler(func=lambda message: message.text == "\U0001F4B4 Оплата")
    def pay(message):
        """ Handles payment button """

        open_dialogue("tg_id", message.chat.id, state="PAY")

        buttons = types.InlineKeyboardMarkup()

        buttons.add(types.InlineKeyboardButton(text="В рублях ₽ или в гривнах ₴", callback_data="rub"))
        buttons.add(types.InlineKeyboardButton(text="В юанях ¥", callback_data="yuan"))
        buttons.add(types.InlineKeyboardButton(text="\U00002753 Связаться с поддержкой", callback_data="sup"))

        bot.send_message(message.chat.id, messages.pay_type, reply_markup=buttons)

    @bot.message_handler(func=lambda message: message.text == "\U0001F193 Пробный период")
    def trial(message):
        """ Handles free trial button """

        buttons = types.InlineKeyboardMarkup()

        buttons.add(types.InlineKeyboardButton(text="\U0001F4B4 Оплата", callback_data="pay"))
        buttons.add(types.InlineKeyboardButton(text="\U00002753 Связаться с поддержкой", callback_data="sup"))

        bot.send_message(message.chat.id, messages.trial_text,
                         reply_markup=buttons, parse_mode='Markdown')

    @bot.message_handler(func=lambda message: message.text == "\U0001F4F0 Узнать больше")
    def blog(message):
        """ Handles blog button """

        buttons = types.InlineKeyboardMarkup()

        buttons.add(types.InlineKeyboardButton(text="Блог", url='url'))

        bot.send_message(message.chat.id, "Узнайте как заблокировать рекламу, какие появились сервера и многое другое",
                         reply_markup=buttons)

    @bot.message_handler(func=lambda message: message.text == "\U0001F1F9\U0001F1F2Для Туркменистана")
    def tm(message):
        """ Handles for Turkmenistan button """

        buttons = types.InlineKeyboardMarkup()

        buttons.add(types.InlineKeyboardButton(text="Сайт обслуживания", url='url'))
        buttons.add(types.InlineKeyboardButton(text="Как подключить?",
                                               url='url'))

        bot.send_message(message.chat.id, messages.turk, reply_markup=buttons)

    @bot.message_handler(func=lambda message: message.text == "\U0001F91D Сотрудничество")
    def coop(message):
        """ Handles cooperation button """

        buttons = types.InlineKeyboardMarkup()

        buttons.add(types.InlineKeyboardButton(text="Сделать предложение", url='url'))

        bot.send_message(message.chat.id, messages.coop, reply_markup=buttons)

    @bot.message_handler(func=lambda message: message.text == "\U0001F6D2 ZGC SHOP")
    def shop(message):
        """ Handles zgc shop button """

        buttons = types.InlineKeyboardMarkup()

        buttons.add(types.InlineKeyboardButton(text="\U0001F6D2 ZGC SHOP", url='https://market.zgc.su/'))
        buttons.add(types.InlineKeyboardButton(text="\U00002753 Связаться с поддержкой", callback_data='market'))

        bot.send_message(message.chat.id, messages.shop, reply_markup=buttons)

    @bot.message_handler(func=lambda message: message.text == "\U00002753 Связаться с поддержкой")
    def sup(message):
        """ Handles support button """

        support(message)

    @bot.callback_query_handler(func=lambda call: True)
    def react(call):
        """ Handles all callback buttons """

        buttons = types.InlineKeyboardMarkup()

        if call.data == "rub":
            bot.send_message(call.message.chat.id, messages.rub_text, parse_mode='Markdown')

        elif call.data == "yuan":
            bot.send_message(call.message.chat.id, messages.yuan_text, parse_mode='Markdown')

        elif call.data == "install":
            bot.send_message(call.message.chat.id, messages.first_install)

        elif call.data == "other":
            bot.send_message(call.message.chat.id, messages.support, parse_mode='Markdown')

        elif call.data == "market":
            open_dialogue("tg_id", call.message.chat.id)
            bot.send_message(call.message.chat.id, 'Здравствуйте! Укажите, пожалуйста, продукт и вопросы по нему')

        elif call.data == "urgent":
            support(call.message, urgent=True)

        elif call.data == "sup":
            support(call.message)

        # If user rated quality less than 5 and pushed feedback button, open dialogue for one message only
        elif call.data == "get_better":
            update_clients(["tg_id", call.message.chat.id],
                           ["state", "ONE MESSAGE"], ["review_time", f"{int(time.time())}"])

            bot.send_message(call.message.chat.id, messages.get_better)

        elif call.data == "pay":
            buttons.add(types.InlineKeyboardButton(text="В рублях или в гривнах", callback_data="rub"))
            buttons.add(types.InlineKeyboardButton(text="В юанях", callback_data="yuan"))
            buttons.add(types.InlineKeyboardButton(text="\U00002753 Связаться с поддержкой", callback_data="sup"))

            bot.send_message(call.message.chat.id, messages.pay_type, reply_markup=buttons)

        elif call.data in ["1", "2", "3", "4", "5"]:

            # User has already rated
            if get_info("rate", "tg_id", call.message.chat.id) != "0":
                bot.send_message(call.message.chat.id, "Вы уже поставили оценку, спасибо!")
                return

            rating = call.data

            # Ask user to make review if he gave the highest rate
            if rating == "5":
                buttons.add(types.InlineKeyboardButton(text="\U0001F49B Оставить отзыв",
                                                       url="url"))

                bot.send_message(call.message.chat.id, "Если вам понравился наш сервис - оставьте отзыв, "
                                                       "и мы предоставим вам 10 дней бесплатного VPN!\n\n"
                                                       "_Когда оставите отзыв свяжитесь с нами для получения бонуса_",
                                 reply_markup=buttons, parse_mode='Markdown')

            # Ask user to write feedback
            else:
                buttons.add(types.InlineKeyboardButton(text="\U0001F4A1 Оставить пожелание", callback_data="get_better"))
                bot.send_message(call.message.chat.id, "Мы можем что-то улучшить в обслуживании?", reply_markup=buttons)

            bot.send_message(config.group_id, f"Клиент `{call.message.chat.id}` поставил вам {rating}",
                             parse_mode='Markdown')
            update_clients(["tg_id", call.message.chat.id], ["rate", rating])


    @bot.message_handler(func=check_mail_edit)
    def mail_edit(message):
        """ Allows bot owner to edit database, deleting row with wrong email and copying IDs to row with correct email
            Start with bot command '/почта', then reply to every bot message """

        if message.text == "/почта":
            temp["true_email"] = ""
            temp["wrong_email"] = ""
            bot.send_message(message.chat.id, messages.edit_wrong_mail)
            return

        reply_text = message.reply_to_message.text

        # First, you must enter wrong email address, existing in DB
        if reply_text == messages.edit_wrong_mail:
            wrong_email_info = db_find_value("email", message.text.lower())

            # Wrong email not found in DB
            if not wrong_email_info:
                bot.send_message(message.chat.id, "Такой почты нет в базе!")
                return

            # Save email info to temp
            temp['wrong_email'] = wrong_email_info

            # Message for the next step
            bot.send_message(message.chat.id, messages.edit_true_mail)

        # Second, you must enter correct email address, existing in DB
        elif reply_text == messages.edit_true_mail:

            # No info about wrong email in temp
            if not temp['wrong_email']:
                bot.send_message(message.chat.id, "Не указан неверный email")
                return

            true_email_info = db_find_value("email", message.text.lower())

            # Correct email not found in DB
            if not true_email_info:
                bot.send_message(message.chat.id, "Такой почты нет в базе!")
                return

            temp['true_email'] = true_email_info
            t = temp['true_email']
            w = temp['wrong_email']

            # Send two messages with DB info about wrong and correct email so we can check everything
            bot.send_message(message.chat.id, f"Данные неправильной почты:\nemail = {w[0]}\ndate = {w[1]}\n"
                                              f"tariff = {w[2]}\nsub = {w[3]}\ntg_id = {w[4]}\nvk_id = {w[5]}\nfb_id = {w[6]}")

            bot.send_message(message.chat.id, f"Данные правильной почты:\nemail = {t[0]}\ndate = {t[1]}\n"
                                              f"tariff = {t[2]}\nsub = {t[3]}\ntg_id = {t[4]}\nvk_id = {t[5]}\nfb_id = {t[6]}")

            # Return if wrong and correct emails have different IDs for the same messenger (tg/vk/fb)
            if w[4] != "0" != t[4] and w[4] != t[4] \
            or w[5] != "0" != t[5] and w[5] != t[5] \
            or w[6] != "0" != t[6] and w[6] != t[6]:
                bot.send_message(message.chat.id, "У этих почт разные айди для одного способа связи, надо разбираться\n")
                return

            # Send message, asking to confirm editing
            bot.send_message(message.chat.id, messages.edit_confirm)

        elif reply_text == messages.edit_confirm:

            # Editing confirmed
            if message.text.lower() == "да":
                t = temp['true_email']
                w = temp['wrong_email']

                # No info about wrong or correct email in temp
                if not t or not w:
                    bot.send_message(message.chat.id, "Не указаны почты")
                    return

                # Record this change to log
                with open("edit_log.txt", "a+") as file:
                    file.write(f"---------------------------\n{datetime.datetime.today()}\n"
                               f"wrong email = {w[0]}\ntrue email = {t[0]}\n")

                tg_id, vk_id, fb_id = w[4], w[5], w[6]
                t_mail = t[0]

                update_clients(["email", t_mail], ["state", "CLOSED"], ["rate", "5"], ["review_time", "0"])

                # Check if ID that we want to copy != 0 and not the same with correct email ID
                if tg_id not in ["0", t[4]]:
                    update_clients(["email", t_mail], ["tg_id", tg_id])
                    print(f"Заменили tg_id {t[4]} на {tg_id}\n")

                if vk_id not in ["0", t[5]]:
                    update_clients(["email", t_mail], ["vk_id", vk_id])
                    print(f"Заменили vk_id {t[5]} на {vk_id}\n")

                if fb_id not in ["0", t[6]]:
                    update_clients(["email", t_mail], ["fb_id", fb_id])
                    print(f"Заменили fb_id {t[6]} на {fb_id}\n")

                bot.send_message(message.chat.id, delete_client("email", w[0]))
                print(f"Удалили запись с почтой {w[0]}")
                temp['wrong_email'], temp['true_email'] = "", ""

            # Editing cancelled
            elif message.text.lower() == "нет":
                bot.send_message(message.chat.id, "Замена почты отменена")
                temp['wrong_email'], temp['true_email'] = "", ""

            else:
                bot.send_message(message.chat.id, "Не понял, повторите")

    @bot.message_handler(func=lambda message: message.chat.id == config.group_id,
                         content_types=['text', 'audio', 'document', 'photo', 'sticker', 'voice', 'video'])
    def support_group(message):
        """ Handle all messages in support group """

        # Bot info message
        if message.text and message.text.lower() == "/info":
            bot.send_message(config.group_id, messages.info)

        # Message is reply to some message
        if message.reply_to_message:
            client_text = message.reply_to_message.text or message.reply_to_message.caption

            if not client_text:
                pass

            elif client_text and client_text.endswith("Web_client"):
                import data_structs as ds
                import helpers

                replied_message = message.reply_to_message.text

                if replied_message == None:
                    replied_message = message.reply_to_message.caption

                reply_email = helpers.get_email_from_message(replied_message)

                ws_message = json.dumps({'from': 'bot', 'message': message.text})

                import asyncio

                asyncio.run(ds.send_ws_msg(reply_email, ws_message))


        # Message is not reply to some message
        else:
            print('some else')


    @bot.message_handler(func=lambda message: get_info("state", "tg_id", message.chat.id) in ["OPEN", "REMINDED", "PAY"],
                         content_types=['text', 'photo', 'video', 'voice', 'audio', 'sticker', 'document'])
    def forward_to_support(message):
        """ Forward all clients messages to support group if dialogue is open
            Also send support info about client tariff """

        tg_to_tg(config.group_id, message)

        # Notify client that his message was received (once per dialogue)
        if get_info("received", "tg_id", message.chat.id) == "NO":
            bot.send_message(message.chat.id, "Ваше сообщение передано в поддержку. "
                                              "Мы постараемся ответить как можно быстрее!")
            update_clients(["tg_id", message.chat.id], ["received", "YES"])

        user_state = get_info("state", "tg_id", message.chat.id)

        # Client sent a message after being reminded about the payment, open dialogue
        if user_state == "REMINDED":
            open_dialogue("tg_id", message.chat.id)

        # Client sent a photo after he has chosen the payment option. Consider this photo as payment screenshot
        elif user_state == "PAY":
            if message.photo:
                #autopay(message)
                print('some in pay state')

    @bot.message_handler(func=lambda message: get_info("state", "tg_id", message.chat.id) == "CLOSED",
                         content_types=['text', 'photo', 'video', 'voice', 'audio', 'sticker', 'document'])
    def push_something(message):
        """ If user identified and dialogue is closed, ask him to use buttons """

        initial_buttons(message, send_text=messages.push_buttons)

    @bot.message_handler(func=lambda message: get_info("state", "tg_id", message.chat.id) == "ONE MESSAGE",
                         content_types=['text', 'photo', 'video', 'voice', 'audio', 'sticker', 'document'])
    def one_message_pass(message):
        """ User pushed the feedback button after previous support conversation was closed.
            Suppose user entering one-message review """

        time_past = int(time.time()) - int(get_info("review_time", "tg_id", message.chat.id))

        # If user pushed the button more than a day ago, don't send his message to support
        if time_past // 3600 >= 24:
            bot.send_message(message.chat.id, messages.buttons_menu)

        else:
            tg_to_tg(config.group_id, message, review=True)
            bot.send_message(message.chat.id, "Спасибо за отзыв!")

        update_clients(["tg_id", message.chat.id], ["state", "CLOSED"])

    # --------------------------------------------------
    while True:
        try:
            bot.infinity_polling(timeout=120)
        except Exception as e:
            print("TG init error, restarting")
            time.sleep(3)


def tg_init():
    while True:
        try:
            telegram()
        except Exception as e:
            print("TG init error, restarting")
            time.sleep(3)


def start_bot():

    t1 = threading.Thread(target=tg_init)

    import ws_chat_server as ws_server

    t5 = threading.Thread(target=ws_server.start_ws_server)
    t5.start()

    t1.start()
    t1.join()




if __name__ == '__main__':



        # Dict containing all tariffs info (for OCR-based payment handling)
        tariffs_base = {}

        # Temp data for mailing and DB editing commands
        temp = {"tariffs": [], "mail_text": "", "wrong_email": "", "true_email": ""}

        # Arrays for different functions
        res, clients_open, info = [], [], []

        # Telegram bot
        bot = telebot.TeleBot(config.tg_token, skip_pending=True)

        t1 = threading.Thread(target=tg_init)

        import ws_chat_server as ws_server

        t5 = threading.Thread(target=ws_server.start_ws_server)
        t5.start()

        t1.start()
        t1.join()


