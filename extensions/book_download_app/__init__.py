from . import book_download_app

def get_app(*args, **kwargs):
    return book_download_app.get_entry_point(*args, **kwargs)

def get_icon():
    return 'images/download_black.png'

def get_description():
    return """Utility to download arbitrary books that are in the corrections workspace"""