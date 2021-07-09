import config
import telebot
import json
import time
import threading

def telegram():
    print("\nTelegram running")

    @bot.message_handler(func=lambda message: message.chat.id == config.group_id,
                         content_types=['text', 'audio', 'document', 'photo', 'sticker', 'voice', 'video'])
    def support_group(message):
        """ Handle all messages in support group """

        # Bot info message
        if message.text and message.text.lower() == "/info":
            bot.send_message(config.group_id, "messages.info")

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
    import ws_chat_server as ws_server

    t1 = threading.Thread(target=tg_init)

    t5 = threading.Thread(target=ws_server.start_ws_server)
    t5.start()

    t1.start()
    t1.join()


def run_bot():
    import ws_chat_server as ws_server

    t1 = threading.Thread(target=tg_init)

    t5 = threading.Thread(target=ws_server.start_ws_server)
    t5.start()

    t1.start()
    t1.join()

if __name__ == '__main__':
    bot = telebot.TeleBot(config.tg_token, skip_pending=True)
    run_bot()
