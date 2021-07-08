import  messages
commands = '''
Оплата, В рублях ₽ или в гривнах ₴, В юанях ¥, Связаться с поддержкой,
Пробный период, 
Узнать больше, Блог,
Для Туркменистана, 
Сотрудничество, 
ZGC SHOP, 
Связаться с поддержкой

'''

# варианты ответа через 2 запятые
command_answers = \
    {
        "/Оплата": { "answer": messages.pay_type, "commands": [("В рублях ₽ или в гривнах ₴",'/rub'), ("В юанях ¥", "/yuan"), ("Связаться с поддержкой",'/Связаться с поддержкой')]},
        "/Пробный период": { "answer": messages.ru_site_trial_text, "commands":[('http://zgcvpn.ru','http://zgcvpn.ru'),("Оплата",'/Оплата'), ("Связаться с поддержкой",'/Связаться с поддержкой')]},
        "/Узнать больше": { "answer": "Узнайте как заблокировать рекламу, какие появились сервера и многое другое", "commands": [["Блог",'https://market.zgc.su/zgcvpnblog']]},
        "/Для Туркменистана":  { "answer": messages.turk, "commands":[("Сайт обслуживания",'https://tm.zgc.su/'), ("Как подключить?",'https://sites.google.com/view/zgcvpn/try?authuser=0')]},
        "/Сотрудничество": { "answer": messages.coop, "commands":[["Сделать предложение",'https://zgcvpn.ru/partnership']]},
        "/ZGC SHOP": { "answer": messages.shop, "commands":[("ZGC SHOP",'https://market.zgc.su/'), ("Связаться с поддержкой", '/market') ]},
        "/Связаться с поддержкой": { "answer": messages.coop, "commands":[("Первичная настройка", "/install"),("Другое", "/other"), ('ZGC SHOP','/market')]},



        "/urgent": {"answer": messages.first_install, "commands":[]},
        "/install": {"answer": messages.first_install, "commands":[]},
        "/other": {"answer": messages.ru_site_support, "commands":[('.', 'https://market.zgc.su/vpnfaq')]},
        "/market": {"answer": 'Здравствуйте! Укажите, пожалуйста, продукт и вопросы по нему', "commands":[]},
        "/rub": {"answer": messages.ru_site_rub_text, "commands":[('Тарифы можно посмотреть тут','https://zgcvpn.ru/#tariffs')]},
        "/yuan": {"answer": messages.ru_site_yuan_text, "commands":[('Alipay:', 'https://zgc.su/pay/alipay.jpeg'), ('WeChat pay:', 'https://zgc.su/pay/wechat.png')]},

    }



en_command_answers = {
        "/Payment": { "answer": messages.en_pay_type, "commands": [("In roubles ₽ or in hryvnia ₴",'/rub'), ("In yuan ¥", "/yuan"), ("Connect to support",'/Contact support')]},
        "/Trial period": { "answer": messages.en_site_trial_text, "commands":[('http://zgcvpn.ru', 'http://zgcvpn.ru'),("Payment",'/Payment'), ("Contact support",'/Contact support')]},
        "/Learn more": { "answer": "Learn how to block ads, which servers have appeared, and much more", "commands": [["Blog",'https://market.zgc.su/zgcvpnblog']]},
        "/For Turkmenistan":  { "answer": messages.en_turk, "commands":[("Service site",'https://tm.zgc.su/'), ("How to connect?",'https://sites.google.com/view/zgcvpn/try?authuser=0')]},
        "/Partnership": { "answer": messages.en_coop, "commands":[["Make an offer",'https://zgcvpn.ru/partnership']]},
        "/ZGC SHOP": { "answer": messages.en_shop, "commands":[("ZGC SHOP",'https://market.zgc.su/'), ("Contact support", '/market') ]},
        "/Contact support": { "answer": messages.en_coop, "commands":[("Initial setup", "/install"),("Other", "/other"), ('ZGC SHOP','/market')]},


        "/urgent": {"answer": messages.first_install, "commands":[]},
        "/install": {"answer": messages.first_install, "commands":[]},
        "/other": {"answer": messages.en_site_support, "commands":[('.', 'https://market.zgc.su/vpnfaq')]},
        "/market": {"answer": 'Hello! Please specify the product and questions about it', "commands":[]},
        "/rub": {"answer": messages.en_site_rub_text, "commands":[('Rates can be viewed here','https://zgcvpn.ru/#tariffs')]},
        "/yuan": {"answer": messages.en_site_yuan_text, "commands":[('Alipay:', 'https://zgc.su/pay/alipay.jpeg'), ('WeChat pay:','https://zgc.su/pay/wechat.png')]},
}


# после такой команты открывается еще и диалог с тех поддержкой
open_dialog_cmds = ["/market"]



viewed_cmds = [ "/Оплата", "/Пробный период", "/Узнать больше",  "/Для Туркменистана", "/Сотрудничество", "/ZGC SHOP", "/Связаться с поддержкой" ]

ws_email_wsClient = {}

def send_ws_msg(client_email, message):
    ws = ws_email_wsClient[client_email]

    return ws.send(message)

def add_ws_conn(email, ws):
    ws_email_wsClient[email] = ws
    #insert code for add pin client
    print('added ws for - ' + email)

def remove_ws_conn(email):
    import helpers

    del ws_email_wsClient[email]
    helpers.send_msg_to_tg("email: "+email + "\n клиент покинул чат")
    # insert code for unpin client



callback_cmd_list = ['/urgent', '/install', '/other', '/market', '/rub', '/yuan', '/sup', '/pay']

all_commands = command_answers.keys()
print(all_commands)

