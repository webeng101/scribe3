from io import StringIO
import json
import datetime, time
from ia_scribe.config.config import Scribe3Configuration

config = Scribe3Configuration()

AVAILABLE_POLICIES = {'daily': '%Y_%m_%d',
                      'weekly': '%Y_%V',
                      'monthly': '%Y_%m',
                      }
DEFAULT_STORAGE_POLICY = 'daily'
ITEM_NAME_SCHEMA = '{mediatype}_{rejection_type}_{bucket}'
ENTRY_NAME_SCHEMA = '{scanner}_{uuid}_{timestamp}_rejection.json'

REQUIRED_MD_FIELDS = ['boxid', 'scanner', 'operator',
                      'scanningcenter', 'reason',]

def _validate_metadata(metadata):
    missing_keys = set(REQUIRED_MD_FIELDS).difference(metadata.keys())

    if missing_keys:
        raise Exception('Incomplete metadata. Missing: {}'.format(
                            ', '.join(missing_keys)))

    return True


def _get_current_bucket(storage_policy=DEFAULT_STORAGE_POLICY):
    active_policy = AVAILABLE_POLICIES[storage_policy]
    current_bucket = datetime.datetime.now().strftime(active_policy)
    return current_bucket


def _get_current_item(session, mediatype, rejection_type):
    current_bucket = _get_current_bucket()
    item_name = ITEM_NAME_SCHEMA.format(mediatype=mediatype,
                                        rejection_type=rejection_type,
                                        bucket=current_bucket)
    item = session.get_item(item_name)
    return item



def _prepare_upload(rejected_item, metadata):
    file_name = ENTRY_NAME_SCHEMA.format(scanner=metadata.get('scanner'),
                                         uuid=rejected_item.uuid,
                                         timestamp=time.time())
    file_content = json.dumps(metadata, indent=4, sort_keys=True)

    file_handler = StringIO(file_content)
    file_handler.name = file_name
    return file_handler


def _upload_event(current_item, upload_target):
    if not current_item.collection:
        result = current_item.upload(upload_target,
                                     metadata={'collection': config.get('books_rejects_collection',
                                                                        'books_rejects_data')},
                                     queue_derive=False
                                 )
    else:
        result = current_item.upload(upload_target)

    return result


def _validate_success(response):
    return True


def send_rejection_event(session, rejected_item,  metadata, rejection_type):
    if not _validate_metadata(metadata):
        return False, Exception('Invalid MD')

    current_item = _get_current_item(session, 'book', rejection_type)

    upload_target = _prepare_upload(rejected_item, metadata)

    response = _upload_event(current_item, upload_target)

    if not _validate_success(response):
        return False, Exception('Failed to push event because {}'.format(response))

    return True, response


if __name__ == '__main__':
    md = {'boxid': 'IA123456',
          'scanner': 'davide-dev.sanfrancisco.archive.org',
          'scanningcenter': 'sanfrancisco',
          'operator': 'davide@archive.org',
          'reason': 'margins too tight',
          }

    send_rejection_event(md)
