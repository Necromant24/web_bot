import threading
import bot
import chat_server

if __name__ == '__main__':


    t1 = threading.Thread(target=chat_server.serve_default)
    t1.start()

    bot.run_bot()

