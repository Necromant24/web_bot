import config
import messages
import telebot
from telebot import types
import json
import datetime
import re
import time
import sys
import os
import threading


# ░█████╗░░█████╗░███╗░░░███╗███╗░░░███╗░█████╗░███╗░░██╗
# ██╔══██╗██╔══██╗████╗░████║████╗░████║██╔══██╗████╗░██║
# ██║░░╚═╝██║░░██║██╔████╔██║██╔████╔██║██║░░██║██╔██╗██║
# ██║░░██╗██║░░██║██║╚██╔╝██║██║╚██╔╝██║██║░░██║██║╚████║
# ╚█████╔╝╚█████╔╝██║░╚═╝░██║██║░╚═╝░██║╚█████╔╝██║░╚███║
# ░╚════╝░░╚════╝░╚═╝░░░░░╚═╝╚═╝░░░░░╚═╝░╚════╝░╚═╝░░╚══╝




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
