from . import boxing_station_app

def get_app(*args, **kwargs):
    return boxing_station_app.get_entry_point(*args, **kwargs)

def get_icon():
    return 'images/baseline_archive_black_48dp.png'

def get_description():
    return """Application to run a Boxing Station to sert rejected books"""