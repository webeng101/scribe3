from . import network_test_app

def get_app(*args, **kwargs):
    return network_test_app.get_entry_point(*args, **kwargs)

def get_icon():
    return 'images/baseline_network_check_black_48dp.png'

def get_description():
    return """Utility to test the network environment"""