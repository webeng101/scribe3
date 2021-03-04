import threading

def start_webserver():
    from ia_scribe.webapi import webapi
    t = threading.Thread(target=webapi.app.run,
                         kwargs={'port':8081},
                         name='WebAPIThread')
    t.daemon = True
    t.start()


