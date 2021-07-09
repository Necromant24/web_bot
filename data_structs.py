
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
