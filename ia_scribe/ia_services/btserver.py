import requests
from internetarchive import get_session
from requests.adapters import HTTPAdapter

from ia_scribe import scribe_globals
from ia_scribe.book.metadata import get_metadata
from ia_scribe.config.config import Scribe3Configuration

config = Scribe3Configuration()

def get_ia_session():
    try:
        assert config.has_key('s3/access_key')
        assert config.has_key('s3/secret_key')
        assert config.has_key('cookie')
        assert config.has_key('email')
    except:
        return None

    ia_session = get_session(config={
        'general': {'secure': True},
        's3': {'access': config.get('s3/access_key'),
             'secret': config.get('s3/secret_key')},
        'cookies': {'logged-in-user': config.get('email'),
                    'logged-in-sig': config.get('cookie')},
                    },
        http_adapter_kwargs = {'max_retries': 10},

        )
    return ia_session


def get_scanner_item(Logger=None):
    identifier = get_metadata(scribe_globals.CONFIG_DIR)['scanner']
    session = get_ia_session()
    scanner_item = session.get_item(identifier)
    return scanner_item


def get_corrections_list(Logger):
    ttscribe_item = get_scanner_item(Logger)
    item_books_list = None
    Logger.info('Pending Download: Begin')

    try:
        Logger.debug('Pending Download: Pending Downloads: {0}.'
                     .format(ttscribe_item.metadata['books']))
        raw_books_list = (ttscribe_item.metadata['books']
                          .replace('[', '').replace(']', ''))
        item_books_list = raw_books_list.split(',')
        item_books_list = [x.strip() for x in item_books_list]
        Logger.debug('Pending Download: Parsed: {0}'
                     .format(item_books_list))
        return item_books_list
    except Exception as e:
        Logger.debug('Pending Download: Pending Downloads: No items found '
                     'in item ({}).'.format(e.args[0]))
        return None


def get_adjacent_scanners(show_all=False):
    try:
        sc = get_metadata(scribe_globals.CONFIG_DIR)['scanningcenter']
        session = get_ia_session()
        query = 'collection:iabooks-btserver AND scanningcenter:{}'.format(sc)
        if show_all:
            scanners = [x['identifier'] for x in session.search_items(query)]
        else:
            scanners = [x['identifier'] for x in session.search_items(query) if x['identifier'].startswith('fold')]
        return sc, scanners
    except Exception as e:
        return False, e

