import config
from flask import Flask, request, send_from_directory, redirect
import json


app = Flask(__name__)
url_prefix = ""


admin_password = '123'

# let url_prefix = "";
# let ws_prefix = "botws/";

@app.route('/')
def hello2():
    return redirect(url_prefix+"/static/chat.html", code=302)

@app.route(url_prefix+'/')
def hello():
    return redirect(url_prefix+"/static/chat.html", code=302)

@app.route(url_prefix+'/commands')
def commands_file():
    return send_from_directory("data_files", "commands.json")


def send_img_to_tg(name, email):
    import telebot
    bot = telebot.TeleBot(config.tg_token)
    message = "email: " + email + "\nWeb_client"

    with open("static/web_files/" + name, 'rb') as f:
        bot.send_photo(chat_id=config.group_id, photo=f, caption=message)


@app.route(url_prefix+"/email", methods=['POST'])
def email():
    client_email = request.json['email']
    return {"status": "some bespoleznyi method"}


@app.route(url_prefix+'/photo', methods=['POST'])
def photo():
    file = request.files['file']
    email = request.form['user']

    file.save("static/web_files/" + file.filename)

    send_img_to_tg(file.filename, email)

    return {"status": "ok", "url": url_prefix+"/static/web_files/" + file.filename}


@app.route(url_prefix+'/support/message', methods=['POST'])
def support_message():
    import telebot

    email = request.json['email']
    message = request.json['message']

    message_data = "💬\n " + message + "\n\n" + "email: " + email + "\n\nWeb_client"

    print(message_data)

    bot = telebot.TeleBot(config.tg_token)
    bot.send_message(config.group_id, message_data)

    return {'status': 'ok'}


@app.route(url_prefix+'/static/<path:path>')
def serve_static(path):
    print(path)
    return send_from_directory('static', path)



# upload data file in data_files/commands.json
@app.route(url_prefix+'/upload_commands', methods = ['POST'])
def upload_commands():
    password = request.json['password']

    if password != admin_password:
        return {'status': 'incorrect password'}

    all_data = request.json['data']
    with open('data_files/commands.json', "w") as f:
        f.write(json.dumps(all_data))

    return {'status': 'ok'}



def serve(app, host, port):
    app.run(host=host, port=port)


def serve_default(host='0.0.0.0', port=5000):
    app.run(host=host, port=port)


if __name__ == '__main__':
    print('starting server')
    serve(app, '0.0.0.0', 5000)