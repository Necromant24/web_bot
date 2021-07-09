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
# def get_open_dialogues():
#     """ Returns list of clients with open dialogues
#         If client has several IDs, pick one with priority tg > vk > fb
#         ID is written in monospaced font (`number`) so we can easily copy it for search"""
#
#     #test code - change test.db to database.db
#     with sql.connect("database.db") as con:
#         cur = con.cursor()
#         cur.execute("SELECT tg_id, vk_id, fb_id FROM clients WHERE state in ('OPEN', 'PAY')")
#         clients_open[:] = cur.fetchall()
#
#         for i, numbers in enumerate(clients_open):
#             if numbers[0] != '0':
#
#                 try:
#                     name = bot.get_chat(numbers[0]).first_name
#                 except Exception as e:
#                     name = "Unknown"
#
#                 clients_open[i] = f"<code>{numbers[0]}</code> {name}"
#                 continue
#
#             elif numbers[1] != '0':
#
#                 try:
#                     name = vk.users.get(user_id=numbers[1])[0]['first_name']
#                 except Exception as e:
#                     name = "Unknown"
#
#                 clients_open[i] = f"<code>{numbers[1]}</code> {name}"
#                 continue
#
#             elif numbers[2] != '0':
#                 clients_open[i] = f"<code>{numbers[2]}</code> FB"
#                 continue
#
#         return clients_open


# --------------------------------------------------
# def update_pinned_top():
#     """ Update upper part of pinned message that contains IDs of clients with open dialogues """
#
#     # Pinned message text is stored in file
#     with open("pinned.txt", "r+") as file:
#         op = get_open_dialogues()
#
#         top = "\U0001F5E3 Открытые диалоги:\n" + "\n".join(op)
#
#
#         bottom = file.read().split("==========")[1]
#         new_full = top + "\n==========" + bottom
#
#     with open("pinned.txt", "w") as file:
#         file.write(new_full)
#
#     try:
#         bot.edit_message_text(new_full, config.group_id, config.pinned_msg, parse_mode='HTML')
#     except Exception as e:
#         error_txt = sys.exc_info()[1].args[0]
#
#         if "message is not modified: specified new message content and reply markup are exactly the same" in error_txt:
#             pass
#
#         else:
#             log_report("Pinned edit", e)


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


# --------------------------------------------------
# def close_dialogue(type_id, id, pay=False, silent=False, notify_admin_group=True):
#     """ Change client state in DB to CLOSED and update pinned message with new info
#         Optionally send client closing message """
#
#     # Return if client not found in DB
#     if not get_info("state", type_id, id):
#         return
#
#     # Point that dialogue is already closed and return to prevent multiple closing messages for client
#     if get_info("state", type_id, id) in ["CLOSED", "ONE MESSAGE"]:
#         bot.send_message(config.group_id, "Диалог уже закрыт")
#         return
#
#     update_clients([type_id, id], ["state", "CLOSED"], ["rate", "0"], ["review_time", "0"], ["received", "NO"])
#
#     if notify_admin_group:
#         bot.send_message(config.group_id, f"Диалог закрыт\n{id}")
#
#     #update_pinned_top()
#
#     # Do not send any message to client
#     if silent:
#         return
#
#     if type_id == "tg_id":
#
#         # Send client message with after payment instruction
#         if pay:
#             update_clients([type_id, id], ["verified", 1])
#             return
#
#         # Ask client to rate support
#         buttons = types.InlineKeyboardMarkup()
#         buttons.add(types.InlineKeyboardButton(text="\U0001F92C 1", callback_data="1"))
#         buttons.add(types.InlineKeyboardButton(text="\U00002639	2", callback_data="2"))
#         buttons.add(types.InlineKeyboardButton(text="\U0001F610 3", callback_data="3"))
#         buttons.add(types.InlineKeyboardButton(text="\U0001F642 4", callback_data="4"))
#         buttons.add(types.InlineKeyboardButton(text="\U0001F600 5", callback_data="5"))
#
#         bot.send_message(id, messages.close, reply_markup=buttons)
#
#     elif type_id == "vk_id":
#
#         if pay:
#             update_clients([type_id, id], ["verified", 1])
#             return
#
#         keyboard = VkKeyboard(inline=True)
#
#         keyboard.add_button("\U0001F92C 1")
#         keyboard.add_line()
#         keyboard.add_button("\U00002639	2")
#         keyboard.add_line()
#         keyboard.add_button("\U0001F610 3")
#         keyboard.add_line()
#         keyboard.add_button("\U0001F642 4")
#         keyboard.add_line()
#         keyboard.add_button("\U0001F600 5")
#
#         vk_send_message(id, messages.close, keyboard=keyboard.get_keyboard())
#
#     elif type_id == "fb_id":
#
#         if pay:
#             update_clients([type_id, id], ["verified", 1])
#             return
#
#         buttons = [Button(title='\U0001F92C Плохо', type='postback', payload='2'),
#                    Button(title='\U0001F610 Нормально', type='postback', payload='4'),
#                    Button(title='\U0001F600 Отлично', type='postback', payload='5')]
#
#         fb_bot.send_button_message(recipient_id=id, text=messages.close, buttons=buttons)


# --------------------------------------------------
# def vk_send_message(user_id, message, keyboard=None):
#     """ Send message to VK user """
#
#     random_id = random.randint(0, 2147483646)
#     vk.messages.send(user_id=int(user_id), random_id=random_id, message=message, keyboard=keyboard)


# --------------------------------------------------
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

    # --------------------------------------------------
    # def tg_to_vk(message, to_id):
    #     """ Send message with attachments to VK """
    #
    #     if message.text:
    #         vk.messages.send(user_id=int(to_id), random_id=random.randint(0, 2147483646), message=message.text)
    #     elif message.photo:
    #         photo_tg_to_vk(to_id, save_file(message), message.caption)
    #     elif message.document:
    #         doc_tg_to_vk(to_id, save_file(message), message.caption)

    # -------------------------------------------------
    # def tg_to_fb(message, to_id):
    #     """ Send text message to FB """
    #
    #     if message.text:
    #         fb_bot.send_text_message(to_id, message.text)

    # -------------------------------------------------
    # def photo_tg_to_vk(user_id, path, message):
    #     """ Upload photo to VK servers and send message """
    #
    #     server = vk.photos.getMessagesUploadServer()
    #     upload = requests.post(server['upload_url'], files={'photo': open(path, 'rb')}).json()
    #     save = vk.photos.saveMessagesPhoto(photo=upload['photo'], server=upload['server'], hash=upload['hash'])[0]
    #     att = f"photo{save['owner_id']}_{save['id']}"
    #
    #     vk.messages.send(user_id=int(user_id), random_id=random.randint(1, 2147483647), message=message,
    #                      attachment=att)

    # -------------------------------------------------
    # def doc_tg_to_vk(user_id, path, message):
    #     """ Upload document to VK servers and send message """
    #
    #     server = vk.docs.getMessagesUploadServer(peer_id=user_id, type="doc")
    #     upload = requests.post(server['upload_url'], files={'file': open(path, 'rb')}).json()
    #     save = vk.docs.save(file=upload['file'])
    #     att = f"doc{save['doc']['owner_id']}_{save['doc']['id']}"
    #
    #     vk.messages.send(user_id=user_id, random_id=random.randint(1, 2147483647), message=message, attachment=att)

    # -------------------------------------------------
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

    # --------------------------------------------------
    # def spam(tariffs_list, text, sender, VK_only=False, TG_only=False):
    #     """ Send message to every known messenger for every client with chosen tariffs """
    #
    #     with sql.connect(config.db_file) as con:
    #         clients_list = []
    #
    #         # Get IDs of every client with chosen tariffs
    #         for t in tariffs_list:
    #             cur = con.cursor()
    #             cur.execute("SELECT tg_id, vk_id, fb_id FROM clients WHERE tariff = ?", (t,))
    #             clients_list += cur.fetchall()
    #
    #     for client in clients_list:
    #         sent = False
    #         if not VK_only and client[0] != "0":
    #             url = f'https://api.telegram.org/bot{config.tg_token}/copyMessage'
    #             requests.post(url, json={"chat_id": f"{client[0]}", "from_chat_id": f"{sender}",
    #                                      "message_id": f"{temp['message_id']}"})
    #             sent = True
    #         if not TG_only and client[1] != "0":
    #             vk.messages.send(user_id=int(client[1]), random_id=random.randint(0, 2147483646), message=text)
    #             sent = True
    #         #elif client[2] != "0":
    #             #fb_bot.send_text_message(client[2], text)  # Temporarily off
    #
    #         # Delay to prevent api errors
    #         if sent:
    #             time.sleep(1)

    # --------------------------------------------------
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

    # ----------------------------------------------
    # def autopay(message):
    #     """ Detect text on image using OCR service
    #         If the image contains numbers that correspond to the current tariffs, consider it as payment
    #         Currently used only for yuan payments """
    #
    #     # Check if the same image has been sent before, and save it
    #     filename = save_file(message, folder=config.pay_imgs_path, check=True)
    #     if filename == "File already in folder":
    #         return
    #
    #     # OCR service payload
    #     payload = {'isOverlayRequired': False,
    #                'apikey': config.ocr_token,
    #                'language': "eng",
    #                'OCREngine': '2'
    #                }
    #
    #     with open(filename, 'rb') as f:
    #         r = requests.post('https://api.ocr.space/parse/image',
    #                           files={filename: f},
    #                           data=payload,
    #                           )
    #     answer = json.loads(r.content.decode())
    #
    #     # Get array of all separate text lines
    #     text_on_image = answer['ParsedResults'][0]['ParsedText'].split()
    #
    #     for line in text_on_image:
    #
    #         # Cut off all non-digit characters from both sides (for those cases when text is like "¥59.00")
    #         while line and line[0] not in '0123456789':
    #             line = line[1:]
    #         while line and line[-1] not in '0123456789':
    #             line = line[:-1]
    #
    #         # Check if text matches the "*.00" pattern, for example "239.00"
    #         if re.match("[0-9]+[.,]00", line):
    #
    #             # Tariffs are in roubles, so convert yuan to roubles, simply multiplying by 10
    #             line = str(int(line[:-3]) * 10)
    #
    #             # Detected number corresponds to the current tariffs, confirm payment
    #             if line in tariffs_base:
    #                 tariff, days, description = tariffs_base[line]
    #                 write_payment(get_info('email', 'tg_id', message.chat.id), line)
    #                 bot.send_message(config.group_id,
    #                                  f"ID `{message.chat.id}` продлен тариф {tariff}, сумма {line}, дней {days}",
    #                                  parse_mode='Markdown')
    #                 time.sleep(1)
    #                 close_dialogue('tg_id', message.chat.id, pay=True, notify_admin_group=False)
    #                 return

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

    # @bot.message_handler(func=check_mailing, content_types=['text', 'photo', 'video', 'voice', 'audio', 'sticker', 'document'])
    # def mailing(message):
    #     """ Sends a message to clients with selected tariffs """
    #
    #     txt = message.text or message.caption
    #
    #     if txt == "/рассылка":
    #         bot.send_message(message.chat.id, messages.mailing_tariffs)
    #         return
    #
    #     client_text = message.reply_to_message.text
    #
    #     if client_text == messages.mailing_tariffs:
    #         temp['tariffs'] = [i.lower() for i in txt.split()]
    #         bot.send_message(message.chat.id, messages.mailing_message)
    #
    #     elif client_text == messages.mailing_message:
    #         temp['message_id'] = message.message_id
    #         temp['mail_text'] = txt
    #         bot.send_message(message.chat.id, f"Следующие тарифы: {', '.join(temp['tariffs'])}\n"
    #                                           f"Получат сообщение:\n{txt}\n\n"
    #                                           f"Продолжить? Да/Нет ответом.\n"
    #                                           f"Чтобы отправить ТОЛЬКО в телеграм или вконтакте, ответьте тг/вк")
    #
    #     elif client_text.startswith("Следующие тарифы:"):
    #         if txt.lower() in ["да", "вк", "тг"]:
    #
    #             if not temp['tariffs'] or not temp['mail_text']:
    #                 bot.send_message(message.chat.id, "Не выбраны тарифы/текст!")
    #                 return
    #             if txt.lower() == "вк":
    #                 spam(temp['tariffs'], temp['mail_text'], message.chat.id, VK_only=True)
    #             elif txt.lower() == 'тг':
    #                 spam(temp['tariffs'], temp['mail_text'], message.chat.id, TG_only=True)
    #             else:
    #                 spam(temp['tariffs'], temp['mail_text'], message.chat.id)
    #             bot.send_message(message.chat.id, "Рассылка отправлена")
    #
    #         elif txt.lower() == "нет":
    #             bot.send_message(message.chat.id, "Рассылка отменена")
    #             temp['tariffs'], temp['mail_text'] = [], ''
    #
    #         else:
    #             bot.send_message(message.chat.id, "Не понял, повторите")

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

            # Reply object message was forwarded from tg
            # elif client_text and client_text.endswith("Telegram") or client_text.endswith("Telegram\U00002705"):
            #
            #     tg_id = client_text.split()[-2]
            #
            #     # User id does not fit 'one or more numeral' regexp
            #     if not re.fullmatch(r"[0-9]+", str(tg_id)):
            #         bot.send_message(config.group_id, "Не удалось отправить сообщение. "
            #                                           "Скорее всего это закрытый аккаунт без айди в подписи")
            #         return
            #
            #     #test code
            #     print(message.text)
            #
            #     # Close dialogue
            #     if message.text and message.text.lower() in ["пока", "/пока", "off", "конец", "/q"]:
            #         close_dialogue("tg_id", tg_id)
            #
            #     # Close payment dialogue
            #     elif message.text and message.text.lower() in ["/оплата", "оп"]:
            #         close_dialogue("tg_id", tg_id, pay=True)
            #
            #     # Close dialogue silently
            #     #elif message.text and message.text.lower() == "/закрыть":
            #
            #     elif (message.text != None) and (message.text.lower() == "/закрыть"):
            #         close_dialogue("tg_id", tg_id, silent=True)
            #
            #     else:
            #
            #         # Check if message was forwarded by bot, not by other user
            #         print(message.reply_to_message.from_user.id)
            #         if message.reply_to_message.from_user.id == config.bot_id:
            #             tg_to_tg(tg_id, message, from_support=True)  # Finally, send answer to client :)
            #             open_dialogue("tg_id", tg_id)
            #
            # # Reply object message was forwarded from VK
            # elif client_text and client_text.endswith("Vkontakte") or client_text.endswith("Vkontakte\U00002705"):
            #     vk_id = client_text.split()[-2]
            #
            #     if message.text and message.text.lower() in ["пока", "off", "конец", "/q"]:
            #         close_dialogue("vk_id", vk_id)
            #
            #     elif message.text and message.text.lower() in ["/оплата", "оп"]:
            #         close_dialogue("vk_id", vk_id, pay=True)
            #
            #     elif message.text and message.text.lower() == "/закрыть":
            #         close_dialogue("vk_id", vk_id, silent=True)
            #
            #     else:
            #         tg_to_vk(message, vk_id)
            #         open_dialogue("vk_id", vk_id)
            #
            # # Reply object message was forwarded from FB
            # elif client_text and client_text.endswith("Facebook"):
            #     fb_id = client_text.split()[-2]
            #
            #     if message.text and message.text.lower() in ["пока", "/пока", "off", "конец", "/q"]:
            #         close_dialogue("fb_id", fb_id)
            #
            #     elif message.text and message.text.lower() in ["/оплата", "оп"]:
            #         close_dialogue("fb_id", fb_id, pay=True)
            #
            #     elif message.text and message.text.lower() == "/закрыть":
            #         close_dialogue("fb_id", fb_id, silent=True)
            #
            #     else:
            #         tg_to_fb(message, fb_id)

            #my code
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
            #
            # # Message text is dialogue closing command
            # if message.text and message.text.lower().split()[0] in ["пока", "/пока", "off", "конец", "/q"]:
            #
            #     # If not replying to some message, closing message must be exactly 2 words
            #     # and contain ID of user whose dialogue we want to close
            #     if len(message.text.lower().split()) != 2:
            #         bot.send_message(message.chat.id, "Отправьте команду и айди через пробел, например:\n"
            #                                           "Пока 1234567")
            #         return
            #
            #     # We don't know which messenger this id belongs to, so just try to close this ID for every type
            #     for id_type in ["tg_id", "vk_id", "fb_id"]:
            #         close_dialogue(id_type, message.text.lower().split()[1])
            #
            # elif message.text and message.text.lower().split()[0] in ["/оплата", "оп"]:
            #     if len(message.text.lower().split()) != 2:
            #         bot.send_message(message.chat.id, "Отправьте команду и айди через пробел, например:\n"
            #                                           "/оплата 1234567")
            #         return
            #
            #     for id_type in ["tg_id", "vk_id", "fb_id"]:
            #         close_dialogue(id_type, message.text.lower().split()[1], pay=True)
            #
            # elif message.text and message.text.lower().split()[0] == "/закрыть":
            #     if len(message.text.lower().split()) != 2:
            #         bot.send_message(message.chat.id, "Отправьте команду и айди через пробел, например:\n"
            #                                           "/закрыть 1234567")
            #         return
            #
            #     for id_type in ["tg_id", "vk_id", "fb_id"]:
            #         close_dialogue(id_type, message.text.lower().split()[1], silent=True)

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


# ██╗░░░██╗██╗░░██╗░█████╗░███╗░░██╗████████╗░█████╗░██╗░░██╗████████╗███████╗
# ██║░░░██║██║░██╔╝██╔══██╗████╗░██║╚══██╔══╝██╔══██╗██║░██╔╝╚══██╔══╝██╔════╝
# ╚██╗░██╔╝█████═╝░██║░░██║██╔██╗██║░░░██║░░░███████║█████═╝░░░░██║░░░█████╗░░
# ░╚████╔╝░██╔═██╗░██║░░██║██║╚████║░░░██║░░░██╔══██║██╔═██╗░░░░██║░░░██╔══╝░░
# ░░╚██╔╝░░██║░╚██╗╚█████╔╝██║░╚███║░░░██║░░░██║░░██║██║░╚██╗░░░██║░░░███████╗
# ░░░╚═╝░░░╚═╝░░╚═╝░╚════╝░╚═╝░░╚══╝░░░╚═╝░░░╚═╝░░╚═╝╚═╝░░╚═╝░░░╚═╝░░░╚══════╝
#
# def vkontakte():
#     """ VK chat bot with reply and inline buttons. Identify user by ID, ask his email, transfer messages to support """
#
#     print("\nVkontakte running")
#
#     def reply_keyboard():
#         """ Return default reply keyboard """
#
#         keyboard = VkKeyboard()
#         keyboard.add_button("\U0001F4B4Оплата")
#         keyboard.add_button("\U0001F193Попробовать")
#         keyboard.add_line()
#         keyboard.add_button("\U0001F1F9\U0001F1F2Туркменистан")
#         keyboard.add_button("\U0001F4F0Узнать больше")
#         keyboard.add_line()
#         keyboard.add_button("\U0001F6D2ZGC SHOP")
#         keyboard.add_button("\U0001F91DСотрудничество")
#         keyboard.add_line()
#         keyboard.add_button("\U00002753Связаться с поддержкой")
#
#         return keyboard.get_keyboard()
#
#     def vk_support(user_id, urgent=False):
#         """ Handles every attempt to open support dialogue. Does not open if not urgent and not in working time """
#
#         keyboard = VkKeyboard(inline=True)
#
#         if not urgent:
#
#             # User trying to contact support in non working time
#             if not 17 <= datetime.datetime.today().hour < 22 or datetime.datetime.today().isoweekday() in [6, 7]:
#                 keyboard.add_button("Срочная связь")
#
#                 vk_send_message(user_id, messages.non_working, keyboard.get_keyboard())
#
#                 return
#
#         open_dialogue("vk_id", user_id)
#
#         keyboard.add_button("Первичная настройка")
#         keyboard.add_line()
#         keyboard.add_button("Другое")
#         keyboard.add_line()
#         keyboard.add_button("ZGC SHOP")
#
#         # Ask user to choose problem type
#         msg = messages.type_support
#         sub = get_info("sub", "vk_id", user_id)
#         if sub != '-' and int(get_info("verified", "vk_id", user_id)):
#             msg += f"\U000026A1 Ваша подписка: {sub}"
#         vk_send_message(user_id, msg, keyboard.get_keyboard())
#
#     def buttons_handler(user_id, button_text):
#         """ Handles all available buttons """
#
#         if button_text == "\U0001F4B4Оплата":
#             open_dialogue("vk_id", user_id, state="PAY")
#
#             keyboard = VkKeyboard(inline=True)
#             keyboard.add_button("В рублях ₽ или в гривнах ₴")
#             keyboard.add_line()
#             keyboard.add_button("В юанях ¥")
#             keyboard.add_line()
#             keyboard.add_button("\U00002753Связаться с поддержкой")
#
#             vk_send_message(user_id, messages.pay_type, keyboard.get_keyboard())
#
#         elif button_text == "В рублях ₽ или в гривнах ₴":
#             vk_send_message(user_id, messages.rub_text_vk, reply_keyboard())
#
#         elif button_text == "В юанях ¥":
#             vk_send_message(user_id, messages.yuan_text_vk, reply_keyboard())
#
#         elif button_text == "\U0001F193Попробовать":
#             keyboard = VkKeyboard(inline=True)
#
#             keyboard.add_button("\U0001F4B4Оплата")
#             keyboard.add_line()
#             keyboard.add_button("\U00002753Связаться с поддержкой")
#
#             vk_send_message(user_id, messages.trial_text_vk, keyboard.get_keyboard())
#
#         elif button_text == "\U00002753Связаться с поддержкой":
#             vk_support(user_id)
#
#         elif button_text == "Срочная связь":
#             vk_support(user_id, urgent=True)
#
#         elif button_text == "Первичная настройка":
#             vk_send_message(user_id, messages.first_install, reply_keyboard())
#
#         elif button_text == "Другое":
#             vk_send_message(user_id, messages.support_vk, reply_keyboard())
#
#         elif button_text == "ZGC SHOP":
#             open_dialogue("vk_id", user_id)
#             vk_send_message(user_id, "Здравствуйте! Укажите, пожалуйста, продукт и вопросы по нему", reply_keyboard())
#
#         elif button_text == "\U0001F4F0Узнать больше":
#             keyboard = VkKeyboard(inline=True)
#
#             keyboard.add_openlink_button("Блог", "url")
#
#             vk_send_message(user_id, "Узнайте как заблокировать рекламу, какие появились сервера и многое другое",
#                             keyboard.get_keyboard())
#
#         elif button_text == "\U0001F1F9\U0001F1F2Туркменистан":
#             keyboard = VkKeyboard(inline=True)
#
#             keyboard.add_openlink_button("Сайт обслуживания", "url")
#             keyboard.add_line()
#             keyboard.add_openlink_button("Как подключить?", "url")
#
#             vk_send_message(user_id, messages.turk, keyboard.get_keyboard())
#
#         elif button_text == "\U0001F6D2ZGC SHOP":
#             keyboard = VkKeyboard(inline=True)
#
#             keyboard.add_openlink_button("\U0001F6D2 ZGC SHOP", "url")
#             keyboard.add_line()
#             keyboard.add_button("Связаться с поддержкой")
#
#             vk_send_message(user_id, messages.shop, keyboard.get_keyboard())
#
#         elif button_text == "Связаться с поддержкой":
#             open_dialogue("vk_id", user_id)
#             vk_send_message(user_id, "Здравствуйте! Укажите, пожалуйста, продукт и вопросы по нему", reply_keyboard())
#
#         elif button_text == "\U0001F91DСотрудничество":
#             keyboard = VkKeyboard(inline=True)
#
#             keyboard.add_openlink_button("Сделать предложение", "url")
#
#             vk_send_message(user_id, messages.coop, keyboard.get_keyboard())
#
#         # If user rated quality less than 5 and pushed feedback button, open dialogue for one message only
#         elif button_text == "\U0001F4A1 Оставить пожелание":
#             vk_send_message(user_id, messages.get_better)
#             update_clients(["vk_id", user_id], ["state", "ONE MESSAGE"], ["review_time", f"{int(time.time())}"])
#
#         # Buttons to rate the quality of support
#         elif button_text in ["\U0001F92C 1", "\U00002639 2", "\U0001F610 3", "\U0001F642 4", "\U0001F600 5"]:
#             keyboard = VkKeyboard(inline=True)
#
#             # User has already rated
#             if get_info("rate", "vk_id", user_id) != "0":
#                 vk_send_message(user_id, "Вы уже поставили оценку, спасибо!")
#                 return
#
#             rating = button_text[-1]
#
#             # Ask user to make review if he gave the highest rate
#             if rating == "5":
#                 keyboard.add_openlink_button("\U0001F49B Оставить отзыв",
#                                              "url")
#
#                 vk_send_message(user_id, "Если вам понравился наш сервис - оставьте отзыв, "
#                                          "и мы предоставим вам 10 дней бесплатного VPN!\n\n"
#                                          "Когда оставите отзыв свяжитесь с нами для получения бонуса",
#                                 keyboard=keyboard.get_keyboard())
#
#             # Ask user to write feedback
#             else:
#                 keyboard.add_button("\U0001F4A1 Оставить пожелание")
#                 vk_send_message(user_id, "Мы можем что-то улучшить в обслуживании?", keyboard=keyboard.get_keyboard())
#
#             bot.send_message(config.group_id, f"Клиент `{user_id}` поставил вам {rating}", parse_mode='Markdown')
#             update_clients(["vk_id", user_id], ["rate", rating])
#
#     def vk_message_handler(event):
#         """ Check if user id in base or ask for email, transfer message to TG group if identified client """
#
#         user_id = event.user_id
#         text = event.message
#
#         # User ID not found in DB
#         if not db_find_value("vk_id", user_id):
#
#             # Check if message text has '@' between some non-space symbols
#             if not text or not re.findall(r"\S+@\S+", text):
#                 vk_send_message(user_id, messages.send_email, reply_keyboard())
#                 return
#
#             # Suppose user entered email, look for it in database
#             email = re.findall(r"\S+@\S+", text)[0].lower()
#             email_info = db_find_value("email", email)
#
#             # Email not found, insert new row in DB with that email and user ID
#             if not email_info:
#                 new_client(email, "vk_id", user_id)
#                 vk_send_message(user_id, messages.buttons_menu, reply_keyboard())
#
#             # Email is already used by user with other ID, ask to immediately contact us
#             elif email_info[5] != "0":
#                 new_client("-", "vk_id", user_id)
#                 open_dialogue("vk_id", user_id)
#                 vk_send_message(user_id, messages.email_already_used, reply_keyboard())
#
#             # Email found in DB and not used by other ID, update DB
#             else:
#                 update_clients(["email", email], ["vk_id", user_id])
#                 vk_send_message(user_id, messages.buttons_menu, reply_keyboard())
#
#             return
#
#         # User pushed button
#         if text in ["\U0001F4B4Оплата", "\U0001F193Попробовать", "\U0001F1F9\U0001F1F2Туркменистан",
#                     "\U0001F4F0Узнать больше", "\U0001F6D2ZGC SHOP", "\U0001F91DСотрудничество",
#                     "\U00002753Связаться с поддержкой", "Срочная связь", "В рублях ₽ или в гривнах ₴",
#                     "В юанях ¥", "Первичная настройка", "Другое", "\U0001F92C 1", "\U00002639 2",
#                     "\U0001F610 3", "\U0001F642 4", "\U0001F600 5", "\U0001F4A1 Оставить пожелание",
#                     "ZGC SHOP", "Связаться с поддержкой"]:
#
#             buttons_handler(user_id, text)
#
#             return
#
#         user_state = get_info("state", "vk_id", user_id)
#         # User identified, dialogue is open, transfer message to support
#         if user_state in ["OPEN", "REMINDED"]:
#             forward_vk_to_tg(event)
#
#             # Notify user that we received his message (once per dialogue)
#             if get_info("received", "vk_id", user_id) == "NO":
#                 vk_send_message(user_id, "Ваше сообщение передано в поддержку. "
#                                          "Мы постараемся ответить как можно быстрее!", reply_keyboard())
#                 update_clients(["vk_id", user_id], ["received", "YES"])
#
#             if user_state == "REMINDED":
#                 open_dialogue("vk_id", user_id)
#
#             return
#
#         # User identified, dialogue is closed, ask him to use buttons
#         if user_state == "CLOSED":
#             vk_send_message(user_id, messages.push_buttons, reply_keyboard())
#
#             return
#
#         # User pushed the feedback button after previous support conversation was closed.
#         # Suppose user entering one-message review
#         if user_state == "ONE MESSAGE":
#             time_past = int(time.time()) - int(get_info("review_time", "vk_id", user_id))
#
#             # If user pushed the button more than a day ago, don't send his message to support
#             if time_past // 3600 >= 24:
#                 vk_send_message(user_id, messages.buttons_menu)
#
#             # Send review to support
#             else:
#                 forward_vk_to_tg(event, review=True)
#                 vk_send_message(user_id, "Спасибо за отзыв!")
#
#             update_clients(["vk_id", user_id], ["state", "CLOSED"])
#
#
#     # --------------------------------------------------
#     def forward_vk_to_tg(event, review=False):
#         """ Send client message to support with attachments and client tariff info """
#
#         user = vk.users.get(user_id=event.user_id)
#
#         # Upper part of the message with emoji and name of the user
#         top = "\U0001F4E2 Отзыв\n" if review else f"\U0001F4AC {user[0]['first_name']} {user[0]['last_name']}\n"
#
#         # Bottom part of the message with id and social network name, so we can reply back
#         check = "\U00002705" if get_info("verified", "vk_id", event.user_id) else ''
#         bottom = f"{str(event.user_id)} Vkontakte{check}"
#         attachments = vk.messages.getById(message_ids=event.message_id)['items'][0]['attachments']
#
#         if attachments:
#
#             att_send = 0
#
#             # Check if already sent caption
#             caption_send = 0
#
#             for att in get_attachments(event.message_id):
#                 if att.get('filter') == 'photo':
#
#                     # Send photo only with ID info caption, without message text
#                     if caption_send:
#                         message = top + "\n" + bottom
#                         bot.send_photo(config.group_id, att.get('url'), caption=message)
#                         att_send = 1
#                         return
#
#                     # Make sure we get string type anyway
#                     text = event.message or ""
#
#                     message = top + text + "\n\n"
#
#                     # Add client tariff info
#                     if not info_too_soon(event.user_id):
#                         message += client_info_msg("vk_id", event.user_id)
#
#                     message += bottom
#                     bot.send_photo(config.group_id, att.get('url'), caption=message)
#                     att_send = 1
#
#                     # Change this so we don't send the same caption with other photo
#                     caption_send = 1
#
#             if not att_send:
#                 text = event.message or ""
#                 message = top + text + "\n_ОТ БОТА: клиент приложил в сообщение вконтакте файл, " \
#                                        "который нельзя отправить в телеграм_\n\n"
#
#                 if not info_too_soon(event.user_id):
#                     message += client_info_msg("vk_id", event.user_id)
#
#                 message += bottom
#                 bot.send_message(config.group_id, message, parse_mode='Markdown')
#
#         else:
#             message = top + event.message + "\n\n"
#
#             # Add client tariff info
#             if not info_too_soon(event.user_id):
#                 message += "\n" + client_info_msg("vk_id", event.user_id)
#
#             message += bottom
#             bot.send_message(config.group_id, message)
#
#     # --------------------------------------------------
#     def get_attachments(msg):
#         """ Collect message media, return list with attachments  """
#
#         msg_attachments = vk.messages.getById(message_ids=msg)['items'][0]['attachments']
#         attach_list = []
#
#         for att in msg_attachments:
#
#             # Collect photos
#             if att.get('type') == 'photo':
#                 max_resolution_img = sorted(att['photo']['sizes'], key=lambda img: img.get('height'))[-1]
#                 max_resolution_img['filter'] = 'photo'
#                 attach_list.append(max_resolution_img)
#
#             # collect voice messages
#             elif att.get('type') == 'audio_message':
#                 att['filter'] = 'audio'
#                 attach_list.append(att)
#
#         return attach_list
#
#     # --------------------------------------------------
#     while True:
#         global vk_session
#         global vk
#
#         try:
#             longpoll = VkLongPoll(vk_session)
#             vk_session = vk_api.VkApi(token=config.token_vk)
#             vk = vk_session.get_api()
#
#             for event in longpoll.listen():
#                 if event.type == VkEventType.MESSAGE_NEW and event.to_me:
#                     vk_message_handler(event)
#
#         except Exception as e:
#             print("VK error")
#             log_report("vk", e)
#             time.sleep(3)


# ███████╗░█████╗░░█████╗░███████╗██████╗░░█████╗░░█████╗░██╗░░██╗
# ██╔════╝██╔══██╗██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔══██╗██║░██╔╝
# █████╗░░███████║██║░░╚═╝█████╗░░██████╦╝██║░░██║██║░░██║█████═╝░
# ██╔══╝░░██╔══██║██║░░██╗██╔══╝░░██╔══██╗██║░░██║██║░░██║██╔═██╗░
# ██║░░░░░██║░░██║╚█████╔╝███████╗██████╦╝╚█████╔╝╚█████╔╝██║░╚██╗
# ╚═╝░░░░░╚═╝░░╚═╝░╚════╝░╚══════╝╚═════╝░░╚════╝░░╚════╝░╚═╝░░╚═╝
#
# def facebook():
#     """" FB chat bot with reply and inline buttons. Identify user by ID, ask his email, transfer messages to support """
#
#     print("\nFacebook running")
#
#     app = Flask(__name__)
#
#     @app.route('/', methods=['GET', 'POST'])
#     def receive_message():
#
#         # Facebook verification
#         if request.method == 'GET':
#             token_sent = request.args['hub.verify_token']
#             return verify_fb_token(token_sent)
#
#         else:
#             output = request.get_json()
#
#             for event in output['entry']:
#                 messaging = event['messaging']
#
#                 for message in messaging:
#                     message_handler(message)
#
#             return "Message Processed"
#
#     # --------------------------------------------------
#     def message_handler(message):
#         """ Check if user ID in base or ask for email, transfer message to TG group if identified client """
#
#         user_id = message['sender']['id']
#
#         # Do not react on our own messages
#         if user_id == config.fb_group_id:
#             return
#
#         text = message['message'].get('text') if message.get('message') else ""
#         payload = message['postback'].get('payload') if message.get('postback') else None
#
#         # User ID not found in DB
#         if not db_find_value("fb_id", user_id):
#
#             # Check if message text has '@' between some non-space symbols
#             if not text or not re.findall(r"\S+@\S+", text):
#                 fb_bot.send_text_message(user_id, messages.send_email)
#                 return
#
#             # Suppose user entered email, look for it in database
#             email = re.findall(r"\S+@\S+", text)[0].lower()
#             email_info = db_find_value("email", email)
#
#             # Email not found, insert new row in DB with that email and user ID
#             if not email_info:
#                 new_client(email, "fb_id", user_id)
#                 send_initial_buttons(user_id)
#
#             # Email is already used by user with other ID, ask to immediately contact us
#             elif email_info[6] != "0":
#                 new_client("-", "fb_id", user_id)
#                 open_dialogue("fb_id", user_id)
#                 fb_bot.send_text_message(user_id, messages.email_already_used)
#
#             # Email found in DB and not used by other ID, update DB
#             else:
#                 update_clients(["email", email], ["fb_id", user_id])
#                 send_initial_buttons(user_id)
#
#             return
#
#         # User pushed buttons
#         if payload in ["pay", "trial", "sup", "turk", "urgent", "other", "rub", "yuan", "install", "sup_other",
#                        "wish", "2", "4", "5"]:
#             buttons_handler(user_id, payload)
#
#             return
#
#         user_state = get_info("state", "fb_id", user_id)
#         # User identified, dialogue is open, transfer message to support
#         if user_state in ["OPEN", "REMINDED", "PAY"]:
#             forward_fb_to_tg(message)
#
#             # Notify user that we received his message (once per dialogue)
#             if get_info("received", "fb_id", user_id) == "NO":
#                 fb_bot.send_text_message(user_id, "Ваше сообщение передано в поддержку. "
#                                                   "Мы постараемся ответить как можно быстрее!")
#                 update_clients(["fb_id", user_id], ["received", "YES"])
#
#             if user_state == "REMINDED":
#                 open_dialogue("fb_id", user_id)
#
#             return
#
#         # User identified, dialogue is closed, ask him to use buttons
#         if user_state == "CLOSED":
#             send_initial_buttons(user_id, reply=True)
#             return
#
#         # User pushed the feedback button after previous support conversation was closed.
#         # Suppose user entering one-message review
#         if user_state == "ONE MESSAGE":
#             time_past = int(time.time()) - int(get_info("review_time", "fb_id", user_id))
#
#             if time_past // 3600 >= 24:
#                 fb_bot.send_text_message(user_id, messages.buttons_menu)
#
#             else:
#                 forward_fb_to_tg(message, review=True)
#                 fb_bot.send_text_message(user_id, "Спасибо за отзыв!")
#
#             update_clients(["fb_id", user_id], ["state", "CLOSED"])
#
#     # --------------------------------------------------
#     def send_initial_buttons(id, reply=False):
#         """ Send message with starting buttons """
#
#         buttons = [Button(title='\U0001F4B4Оплата', type='postback', payload='pay'),
#                    Button(title='\U00002753Поддержка', type='postback', payload='sup'),
#                    Button(title='Другое', type='postback', payload='other')]
#
#         text = messages.push_buttons if reply else messages.buttons_menu
#         fb_bot.send_button_message(recipient_id=id, text=text, buttons=buttons)
#
#     # --------------------------------------------------
#     def support(user_id, urgent=False):
#         """ Handles every attempt to open support dialogue. Do not open if not urgent and not in working time """
#
#         if not urgent:
#
#             # User trying to contact support in non working time
#             if not 17 <= datetime.datetime.today().hour < 22 or datetime.datetime.today().isoweekday() in [6, 7]:
#                 buttons = [Button(title='Срочно', type='postback', payload='urgent')]
#
#                 fb_bot.send_button_message(user_id, messages.non_working, buttons)
#
#                 return
#
#         open_dialogue("fb_id", user_id)
#
#         buttons = [Button(title='Настройка', type='postback', payload='install'),
#                    Button(title='Другое', type='postback', payload='sup_other')]
#
#         # Ask user to choose problem type
#         msg = messages.type_support
#         sub = get_info("sub", "fb_id", user_id)
#         if sub != '-' and int(get_info("verified", "fb_id", user_id)):
#             msg += f"\U000026A1 Ваша подписка: {sub}"
#         fb_bot.send_button_message(user_id, msg, buttons)
#
#     # --------------------------------------------------
#     def buttons_handler(user_id, payload):
#         """ Handles all available buttons """
#
#         if payload == "pay":
#             open_dialogue("fb_id", user_id, state="PAY")
#
#             buttons = [Button(title='Рубли ₽ / Гривны ₴', type='postback', payload='rub'),
#                        Button(title='Юани ¥', type='postback', payload='yuan'),
#                        Button(title='\U00002753Поддержка', type='postback', payload='sup')]
#
#             fb_bot.send_button_message(user_id, messages.pay_type, buttons)
#
#         elif payload == "trial":
#
#             buttons = [Button(title='\U0001F4B4Оплата', type='postback', payload='pay'),
#                        Button(title='\U00002753Поддержка', type='postback', payload='sup')]
#
#             fb_bot.send_button_message(user_id, messages.trial_text_vk, buttons)
#
#         elif payload == "turk":
#
#             buttons = [Button(title="Сайт обслуживания", type='web_url', url="url"),
#                        Button(title="Как подключить?", type='web_url',
#                               url="url")]
#             fb_bot.send_button_message(user_id, messages.turk, buttons)
#
#         elif payload == "sup":
#             support(user_id)
#
#         elif payload == "urgent":
#             support(user_id, urgent=True)
#
#         elif payload == "other":
#
#             buttons= [Button(title='\U0001F193Попробовать', type='postback', payload='trial'),
#                       Button(title='\U0001F1F9\U0001F1F2Туркменистан', type='postback', payload='turk'),
#                       Button(title='\U0001F6D2ZGC SHOP', type='web_url', url='url')]
#             fb_bot.send_button_message(user_id, messages.buttons_menu, buttons)
#
#         elif payload == "rub":
#             fb_bot.send_text_message(user_id, messages.rub_text_vk)
#
#         elif payload == "yuan":
#             fb_bot.send_text_message(user_id, messages.yuan_text_vk)
#
#         elif payload == "install":
#             fb_bot.send_text_message(user_id, messages.first_install)
#
#         elif payload == "sup_other":
#             fb_bot.send_text_message(user_id, messages.support_vk)
#
#         # If user rated quality less than 5 and pushed feedback button, open dialogue for one message only
#         elif payload == "wish":
#             fb_bot.send_text_message(user_id, messages.get_better)
#             update_clients(["fb_id", user_id], ["state", "ONE MESSAGE"], ["review_time", f"{int(time.time())}"])
#
#         # Buttons to rate the quality of support
#         elif payload in ["2", "4", "5"]:
#
#             # User has already rated
#             if get_info("rate", "fb_id", user_id) != "0":
#                 fb_bot.send_text_message(user_id, "Вы уже поставили оценку, спасибо!")
#                 return
#
#             # Ask user to make review if he gave the highest rate
#             if payload == "5":
#                 buttons = [Button(title="\U0001F49B Отзыв", type='web_url',
#                                   url="url")]
#
#                 fb_bot.send_button_message(user_id, "Если вам понравился наш сервис - оставьте отзыв, "
#                                                     "и мы предоставим вам 10 дней бесплатного VPN!\n\n"
#                                                     "Когда оставите отзыв свяжитесь с нами для получения бонуса",
#                                            buttons)
#
#             # Ask user to write feedback
#             else:
#                 buttons = [Button(title='\U0001F4A1 Пожелание', type='postback', payload='wish')]
#                 fb_bot.send_button_message(user_id, "Мы можем что-то улучшить в обслуживании?", buttons)
#
#             bot.send_message(config.group_id, f"Клиент `{user_id}` поставил вам {payload}", parse_mode='Markdown')
#             update_clients(["fb_id", user_id], ["rate", payload])
#
#     # --------------------------------------------------
#     def forward_fb_to_tg(message, review=False):
#         """ Send client message to support with client tariff info"""
#
#         user_id = message['sender']['id']
#
#         # Get user info by FB ID
#         req = requests.get(
#             f"https://graph.facebook.com/{user_id}?fields=first_name,last_name&access_token={config.fb_access_token}")
#         user_info = json.loads(req.text)
#
#         # Upper part of the message with emoji and name of the user
#         top = "\U0001F4E2 Отзыв\n" if review else f"\U0001F4AC {user_info['first_name']} {user_info['last_name']}\n"
#
#         # Bottom part of the message with id and social network name, so we can reply back
#         bottom = f"{str(user_id)} Facebook"
#
#         text = message['message'].get('text') or ''
#         attachments = message['message'].get('attachments')
#
#         if attachments:
#
#             # Check if already sent caption
#             caption_send = 0
#
#             for att in attachments:
#                 message = top
#
#                 # Send photo only with ID info caption, without message text
#                 if not caption_send:
#                     message += text + "\n"
#
#                     # Change this so we don't send the same caption with other photo
#                     caption_send = 1
#
#                 message += "\n"
#
#                 # Add client tariff info
#                 if not info_too_soon(user_id):
#                     message += "\n" + client_info_msg("fb_id", user_id)
#
#                 message += bottom
#
#                 if att['type'] == 'image':
#                     bot.send_photo(config.group_id, att['payload']['url'], message)
#         else:
#             message = top + text + "\n\n"
#
#             # Add client tariff info
#             if not info_too_soon(user_id):
#                 message += "\n" + client_info_msg("fb_id", user_id)
#
#             message += bottom
#
#             bot.send_message(config.group_id, message)
#
#     # --------------------------------------------------
#     def verify_fb_token(token_sent):
#         """ FB verification function """
#         if token_sent == config.fb_verify_token:
#             return request.args['hub.challenge']
#         else:
#             return 'Invalid verification token'
#
#     # --------------------------------------------------
#     if __name__ == '__main__':
#         app.run(port=6262,
#                 ssl_context=('two files'))


# ██████╗░░█████╗░████████╗░█████╗░██████╗░░█████╗░░██████╗███████╗
# ██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔════╝
# ██║░░██║███████║░░░██║░░░███████║██████╦╝███████║╚█████╗░█████╗░░
# ██║░░██║██╔══██║░░░██║░░░██╔══██║██╔══██╗██╔══██║░╚═══██╗██╔══╝░░
# ██████╔╝██║░░██║░░░██║░░░██║░░██║██████╦╝██║░░██║██████╔╝███████╗
# ╚═════╝░╚═╝░░╚═╝░░░╚═╝░░░╚═╝░░╚═╝╚═════╝░╚═╝░░╚═╝╚═════╝░╚══════╝
#
# def database():
#     """ Update local database every minute and check for expiring tariffs """
#
#     print("\nDatabase running")
#
#     def update_db():
#         """ First add new clients to DB, then update those who are not clients anymore """
#
#         # Get current tariffs info
#         global tariffs_base
#         fin_acc = gc.open_by_key("key").worksheet('Тарифы')
#         tariffs_base = {i[0]: [i[1], i[2], i[3]] for i in fin_acc.get_all_values()[1:]}
#         print("Tariffs updated")
#
#         # Get all actual clients info
#         all_values = acc.get_all_values()[4:]
#         email = [i[4].lower() for i in all_values]
#         date = [i[5] for i in all_values]
#         tariff = [i[2] for i in all_values]
#         sub = [i[6] for i in all_values]
#
#         with sql.connect(config.db_file) as con:
#             cur = con.cursor()
#             cur.execute("SELECT * FROM clients")
#             res = cur.fetchall()
#
#             db_emails = [i[0] for i in res]
#
#             # Check for every client from google sheets
#             for i, address in enumerate(email):
#                 client = (address, date[i], tariff[i], sub[i], 0, 0, 0, "CLOSED", "0", "0", "NO", 0)
#
#                 # Insert new row
#                 if address not in db_emails:
#                     cur.execute("INSERT INTO clients VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", client)
#                     print(f"New client: {client[:3]}")
#
#                 # Update existing row
#                 else:
#                     cur.execute("UPDATE clients SET date = ?, tariff = ?, sub = ? WHERE email = ?",
#                                 client[1:4] + client[0:1])
#
#             # Check for every client from DB that is off from google sheets and update his tariff info in DB
#             for i, address in enumerate(db_emails):
#                 if address not in email:
#
#                     cur.execute("UPDATE clients SET date = '-', tariff = '-', sub = '-' WHERE email = ?",
#                                 (address,))
#
#     # --------------------------------------------------
#     def reminder():
#         """ Gather info about expiring tariffs and notify clients """
#
#         with sql.connect(config.db_file) as con:
#             cur = con.cursor()
#             cur.execute("SELECT date, tg_id, vk_id, fb_id FROM clients")
#             clients = cur.fetchall()
#
#         today = datetime.datetime.today()
#
#         for cl in clients:
#
#             # Not our client anymore
#             if cl[0] == "-":
#                 continue
#
#             date = cl[0].split('.')  # Date is stored in dd.mm.yyyy format
#             date = datetime.datetime(int(date[2]), int(date[1]), int(date[0]), 0, 0, 0)
#
#             time_left = date - today
#             time_left = (time_left.days * 24 * 60 * 60) + time_left.seconds
#
#             notify_clients("tg_id", cl[1], time_left)
#             notify_clients("vk_id", cl[2], time_left)
#             notify_clients("fb_id", cl[3], time_left)
#
#         # Update pinned message with info about those who were reminded
#         if notified_clients:
#             text = "\U0001F514 Напомнил об оплате:\n"
#             for i in notified_clients:
#                 text += i + "\n"
#
#             #update_pinned_bottom(text)
#
#     # --------------------------------------------------
#     def notify_clients(type_id, id, time_left):
#         """ Check if time_left is 3 days or 1 day in seconds (minus 18 hours so we remind at 18:00 Beijing).
#          Gap is 59 seconds because cycle repeats every 60 seconds, so it will not repeat on 1-60 'borders' """
#
#         if id == "0":
#             return
#
#         message = ""
#
#         if 194341 <= time_left <= 194400:  # 3 days left
#             message = messages.left3days
#         elif 21541 <= time_left <= 21600:  # 1 day left
#             message = messages.left1day
#         elif -64859 <= time_left <= -64800:  # Tariff expired
#             message = messages.left_today
#
#         if message:
#             if type_id == "tg_id":
#                 buttons = types.InlineKeyboardMarkup()
#                 buttons.add(types.InlineKeyboardButton(text="\U0001F4B4 Оплата", callback_data="pay"))
#                 bot.send_message(int(id), message, reply_markup=buttons)
#             elif type_id == "vk_id":
#                 keyboard = VkKeyboard(inline=True)
#                 keyboard.add_button("\U0001F4B4Оплата")
#                 vk_send_message(id, message, keyboard.get_keyboard())
#             elif type_id == "fb_id":
#                 fb_bot.send_text_message(int(id), message)
#
#             update_clients([type_id, id], ['state', 'REMINDED'])
#             notified_clients.add(get_info("email", type_id, id))
#
#             print(f"Notification sent to {type_id} {id}\n")
#
#
#     # --------------------------------------------------
#     while True:
#         update_db()
#
#         # Update DB every 15 minutes
#         for i in range(15):
#             notified_clients = set()
#             reminder()
#             time.sleep(60)


# --------------------------------------------------
def tg_init():
    while True:
        try:
            telegram()
        except Exception as e:
            print("TG init error, restarting")
            time.sleep(3)


# --------------------------------------------------
# def vk_init():
#     while True:
#         try:
#             vkontakte()
#         except Exception as e:
#             print("VK init error, restarting")
#             time.sleep(3)


# --------------------------------------------------
# def fb_init():
#     while True:
#         try:
#             facebook()
#         except Exception as e:
#             print("FB init error, restarting")
#             time.sleep(3)


# --------------------------------------------------
# def db_init():
#     while True:
#         try:
#             database()
#
#         except Exception as e:
#             print("DB init error, restarting")
#             time.sleep(60)


# --------------------------------------------------


#my code
def start_bot():
    # Dict containing timestamp when we added client's tariff information to the message
    clients_info_time = {}

    # Dict containing all tariffs info (for OCR-based payment handling)
    tariffs_base = {}

    # Temp data for mailing and DB editing commands
    temp = {"tariffs": [], "mail_text": "", "wrong_email": "", "true_email": ""}

    # Arrays for different functions
    res, clients_open, info = [], [], []

    # Telegram bot
    #bot = telebot.TeleBot(config.tg_token, skip_pending=True)

    # Vkontakte bot
    # vk_session = vk_api.VkApi(token=config.token_vk)
    # vk = vk_session.get_api()

    # Facebook bot
    #fb_bot = Bot(config.fb_access_token)

    # Google sheets authorization
    # gc = gspread.service_account(filename=config.cred_final)
    # acc = gc.open_by_key("key").worksheet('v2clients')

    t1 = threading.Thread(target=tg_init)
    # t2 = threading.Thread(target=vk_init)
    # t3 = threading.Thread(target=fb_init)
    # t4 = threading.Thread(target=db_init)

    import ws_chat_server as ws_server

    t5 = threading.Thread(target=ws_server.start_ws_server)
    t5.start()

    t1.start()
    # t2.start()
    # t3.start()
    # t4.start()

    t1.join()
    # t2.join()
    # t3.join()
    # t4.join()



if __name__ == '__main__':


        # Dict containing timestamp when we added client's tariff information to the message
        clients_info_time = {}

        # Dict containing all tariffs info (for OCR-based payment handling)
        tariffs_base = {}

        # Temp data for mailing and DB editing commands
        temp = {"tariffs": [], "mail_text": "", "wrong_email": "", "true_email": ""}

        # Arrays for different functions
        res, clients_open, info = [], [], []

        # Telegram bot
        bot = telebot.TeleBot(config.tg_token, skip_pending=True)

        # Vkontakte bot
        # vk_session = vk_api.VkApi(token=config.token_vk)
        # vk = vk_session.get_api()

        # Facebook bot
        # fb_bot = Bot(config.fb_access_token)

        # Google sheets authorization
        # gc = gspread.service_account(filename=config.cred_final)
        # acc = gc.open_by_key("key").worksheet('v2clients')

        t1 = threading.Thread(target=tg_init)
        # t2 = threading.Thread(target=vk_init)
        # t3 = threading.Thread(target=fb_init)
        # t4 = threading.Thread(target=db_init)

        import ws_chat_server as ws_server

        t5 = threading.Thread(target=ws_server.start_ws_server)
        t5.start()

        t1.start()
        # t2.start()
        # t3.start()
        # t4.start()

        t1.join()
        # t2.join()
        # t3.join()
        # t4.join()







