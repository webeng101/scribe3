from . import pong_app

def get_app(*args, **kwargs):
    return pong_app.get_entry_point()

def get_icon():
    return 'images/fidget.png'

def get_description():
    return """Oldies but goldies: a simple and fairly unusable two-players game of pong."""