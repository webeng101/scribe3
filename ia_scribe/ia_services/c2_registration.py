import requests
import json
from internetarchive import get_user_info
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe import scribe_globals

from kivy import Logger

config = Scribe3Configuration()

REGISTER_URL = '{}/register'.format(scribe_globals.C2_REGISTRATION_API)
INFO_URL = '{}/info'.format(scribe_globals.C2_REGISTRATION_API)


def ircize_name(name):
    REPLACE_TABLE = [('@', ''),
                     ('archive.org', ''),
                     ('.', '_'),
                     ]
    cleansed_name = name
    for entry in REPLACE_TABLE:
        token, replacement = entry
        cleansed_name = cleansed_name.replace(token, replacement)
    return cleansed_name


def is_registered():
    if not config.get('c2_name'):
        return False
    if not config.get('c2_password'):
        return False
    user_info = get_user_info(access_key=config.get('s3/access_key'),
                              secret_key=config.get('s3/secret_key'))
    name = ircize_name(user_info.get('username'))
    url = '{}/{}'.format(INFO_URL, name)
    response = requests.get(url)
    exists = json.loads(response.text)
    return exists


def register(s3_access=config.get('s3/access_key'),
             s3_secret= config.get('s3/secret_key') ):

    if is_registered():
        return True

    post_body = {
        's3_access': s3_access,
        's3_secret': s3_secret,
    }
    res = requests.post(REGISTER_URL, data=post_body)
    response_content = json.loads(res.text)
    if response_content.get('error') != None:
        raise Exception(response_content.get('error'))
    token = response_content.get('token')
    username = response_content.get('name')
    if username == None or token == None:
        raise Exception('Username or token are empty')
    config.set('c2_password', token)
    config.set('c2_name', username)

def verify_registration():
    try:
        if is_registered():
            return True, None
        register()
        return True, None
    except Exception as e:
        Logger.exception(e)
        return False, e