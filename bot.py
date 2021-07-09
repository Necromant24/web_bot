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

        #open_dialogue("tg_id", message.chat.id)

        buttons = types.InlineKeyboardMarkup()
        buttons.add(types.InlineKeyboardButton(text="Первичная настройка", callback_data="install"))
        buttons.add(types.InlineKeyboardButton(text="Другое", callback_data="other"))
        buttons.add(types.InlineKeyboardButton(text="ZGC SHOP", callback_data="market"))

        # Ask user to choose problem type
        msg = messages.type_support
        #sub = get_info("sub", "tg_id", message.chat.id)
        #if sub != '-' and int(get_info("verified", "tg_id", message.chat.id)):
        #    msg += f"\U000026A1 Ваша подписка: {sub}"
        #bot.send_message(message.chat.id, msg, reply_markup=buttons)

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
