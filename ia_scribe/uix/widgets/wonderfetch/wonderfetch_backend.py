from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.scribe_globals import OL_DEDUPE_URL
import json, requests

config = Scribe3Configuration()


def generic_validator(func):
    def func_wrapper(*args, **kwargs):
        response = args[0]
        if response['status'] not in ['ok', 'OK']:
            return -2
        if 'response' not in response:
            return -2
        else:
            return func(*args, **kwargs)

    return func_wrapper


@generic_validator
def validate_response_dwwi(response):
    return response['response']


@generic_validator
def validate_response_ol(response):
    return response['response']


AVAILABLE_APIS = {
    # 'dwwi': {'validator': validate_response_dwwi, },
    'ol': {'validator': validate_response_ol, },

}


def build_list(books_list):
    if len(books_list) == 0:
        return []

    DISPLAY_FIELDS = ['title', 'creator', 'volume', 'imagecount']

    def build_value(book_metadata):
        item_md_fields = {k: v for k, v in book_metadata['metadata'].items() if k in DISPLAY_FIELDS}
        dwwi_md = {k: v for k, v in book_metadata.items() if k in DISPLAY_FIELDS}
        return item_md_fields

    URL = 'https://archive.org/services/img/{}'
    ret = []
    for identifier, book_metadata in books_list.items():
        entry = {
            'image': URL.format(identifier),
            'key': identifier,
            'value': build_value(book_metadata),
        }
        ret.append(entry)
    return ret


def select_api(name, **kwargs):
    if name == 'isbn':
        ret = OL_DEDUPE_URL + '?search_id={}&catalog=isbn'
        ret += '&debug=true'
    elif 'ol':
        if not kwargs.get('catalog', None):
            ret = OL_DEDUPE_URL + '?search_id={}'
        else:
            ret = OL_DEDUPE_URL + '?catalog={0}&search_id={{}}'.format(kwargs['catalog'])
    ret += '&old_pallet={}'.format(kwargs['old_pallet'])
    return ret

def get_api_result(api, id, **kwargs):
    base_url = select_api(api, **kwargs)
    concrete_url = base_url.format(id)

    try:
        response = json.loads(requests.get(concrete_url).text)
        return True, response
    except requests.exceptions.ConnectionError as e:
        return False, e
    except AttributeError as e:
        return False, e
    except Exception as e:
        return False, e


def parse_response(response, api=None):
    api = 'ol' if api is None else api
    validator = AVAILABLE_APIS.get(api)['validator']
    return validator(response)
