from . import label_app

def get_app(*args, **kwargs):
    return label_app.get_entry_point(*args, **kwargs)

def get_icon():
    return 'images/label_black.png'

def get_description():
    return """Utility to print labels for books by IA identifier"""