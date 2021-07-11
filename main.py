import threading
import bot
import chat_server

if __name__ == '__main__':
    t1 = threading.Thread(target=bot.run_bot)
    t1.start()

    chat_server.serve_default()

