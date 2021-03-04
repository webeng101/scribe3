import os
import random
import re
import string

import time
import traceback
from datetime import datetime
import requests

from ia_scribe.book.metadata import (
    get_metadata,
    set_metadata,
    get_sc_metadata,
)

from ia_scribe.tasks.book_tasks.petabox import get_pending_catalog_tasks
from ia_scribe.book.scandata import ScanData
from ia_scribe.ia_services.iabdash import push_event
from ia_scribe import scribe_globals
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.exceptions import ScribeException
from ia_scribe.book.upload_status import UploadStatus
from ia_scribe.ia_services.btserver import get_ia_session
from ia_scribe.notifications.notifications_manager import NotificationManager

from os.path import join

config = Scribe3Configuration()
notifications_manager = NotificationManager()


def _get_email():
    return config.get('email')


def _set_upload_lock_file(book, Logger):
    Logger.debug('Setting upload lock file')
    with open(join(book['path'], "upload_lock"), 'w+') as fp:
        pid_path = os.path.join(scribe_globals.CONFIG_DIR, 'scribe_pid')
        with open(pid_path) as f:
            pid_num = str(f.read().strip())
            fp.write(pid_num)


def _push_metrics(book, scandata,encoded_md, sizes_dict, doing_foldouts,
                  responses, responses_dict, book_upload_phase_start,
                  book_upload_phase_end, book_upload_total_start,
                  book_preimage_upload_start, book_preimage_upload_end):
    if os.path.exists(join(book['path'], 'time.log')):
        with open(join(book['path'], 'time.log'), 'r') as fp:
            global_time_open = float(fp.readline())
    else:
        global_time_open = None

    for item in responses:
        try:
            for r in item:
                responses_dict[str(r.request.url)] = r.status_code
        except:
            responses_dict[item] = 'Error'
    book_upload_total_end = time.time()

    times_dict = {'upload_phase': book_upload_phase_end - book_upload_phase_start,
                  'total': book_upload_total_end - book_upload_total_start,
                  'preimage': book_preimage_upload_end - book_preimage_upload_start,
                  }

    payload = {
        'local_id': book['uuid'], 'status': book['status'],
        'activeTime': global_time_open,
        'leafNum': scandata.count_pages(),
        'metadata': encoded_md,
        'responses': responses_dict,
        'times': times_dict,
        'sizes': sizes_dict,
        'foldouts': doing_foldouts,
    }
    push_event('tts-book-uploaded', payload,
               'book', book['identifier'])

def _verify_responses(responses, Logger):
    flat_responses = [y for x in responses for y in x]

    Logger.info('Upload book: Verifying {} responses were all 200 OK...'.format(len(flat_responses)))

    for response in flat_responses:
        if response.status_code not in [200, 499]:
            raise Exception('Upload book: Response code {} {} - {} from cluster. '
                            'URL was: {} | content: {}'
                            'This is an error and the book will be moved to an error state.'
                            .format(response.status_code,
                                    response.reason,
                                    response.text if 'text' in response else "",
                                    response.url,
                                    response.content))

def _upload_book_files(zip_path, book, encoded_md, item, responses,
                       metasource_file_location,metasource_file_upload_name,
                       Logger):
    sizes_dict = {
        'preimage': os.path.getsize(zip_path),
    }

    book_preimage_upload_start = time.time()

    m = 'Uploading preimage.zip to {}'.format(book['identifier'])
    Logger.debug(m)
    # Clock.schedule_once(partial(self.set_status_callback, m))
    book.update_message('Upload | Images file')
    upload_response = item.upload(
        zip_path, metadata=encoded_md, retries=10,
        retries_sleep=60, queue_derive=False, verbose=True, verify=True,
        headers= {'x-archive-keep-old-version': '1'}
    )
    if len(upload_response)== 0 or getattr(upload_response[0], 'url') is None:
        if not book.force_upload:
            raise ScribeException('No response was returned by IA upon upload of preimage.zip. '
                              'This could mean the file has already been uploaded, the item is not '
                              'available, your cookie could have expired. '
                              'Refer to the documentation for further guidance.')

    responses.append(upload_response)
    url_to_status_code = \
        {r.request.url: r.status_code for r in upload_response}
    book.logger.debug(
        'Response from upload: {} | {}'
            .format(upload_response, url_to_status_code)
    )

    book_preimage_upload_end = time.time()

    book.update_message('Upload | Metasource')
    if metasource_file_location is not None:
        book.logger.debug(
            'Uploading metasource file {0} as {1}'
                .format(metasource_file_location,
                        metasource_file_upload_name)
        )
        response = item.upload(
            {metasource_file_upload_name: metasource_file_location},
            retries=10, retries_sleep=60, queue_derive=False, verify=True, verbose=True,
        )
        responses.append(response)
        url_to_status_code = \
            {r.request.url: r.status_code for r in response}
        book.logger.debug('Response from upload: {} | {}'
                          .format(response, url_to_status_code))

    book.update_message('Upload | MARCs')

    if os.path.exists(os.path.join(book['path'], 'marc.bin')):
        book.logger.debug(
            'Uploading MARC Binary file {}'
                .format(join(book['path'],
                             book['identifier'] + '_marc.bin'))
        )
        upload_name_mapping = \
            {book['identifier'] + '_meta.mrc': join(book['path'],
                                                    'marc.bin')}
        response = item.upload(upload_name_mapping, retries=10,
                               retries_sleep=60, queue_derive=False, verify=True, verbose=True, )
        responses.append(response)
        url_to_status_code = \
            {r.request.url: r.status_code for r in response}
        book.logger.debug('Response from upload: {} | {}'
                          .format(response, url_to_status_code))

    if os.path.exists(os.path.join(book['path'], 'marc.xml')):
        book.logger.debug(
            'Uploading MARCXML file {} to {}'
                .format(join(book['path'], 'marc.xml'),
                        join(book['identifier'] + '_marc.xml'))
        )
        upload_name_mapping = \
            {book['identifier'] + '_marc.xml': join(book['path'],
                                                    'marc.xml')}
        response = item.upload(upload_name_mapping, retries=10,
                               retries_sleep=60, queue_derive=False,verify=True, verbose=True, )
        responses.append(response)
        url_to_status_code = \
            {r.request.url: r.status_code for r in response}
        book.logger.debug('Response from upload: {} | {}'
                          .format(response, url_to_status_code))

    send_to_station_file = os.path.join(book['path'], 'send_to_station')
    if os.path.exists(send_to_station_file):
        target_scanner = None
        with open(send_to_station_file, 'r') as f:
            target_scanner = f.read()
            assert target_scanner != None
        book.update_message('Upload | Sending foldouts to {}'.format(target_scanner))
        Logger.info('Book uploader: found instructions to send {} to {}'
                    .format(book['identifier'], target_scanner))

        book.logger.debug(
            'Uploading send-to-scribe.txt file {} to {}'
                .format(send_to_station_file,
                        book['identifier'])
        )
        upload_name_mapping = \
            {book['identifier'] + '_sent_to.txt': send_to_station_file}
        response = item.upload(upload_name_mapping, retries=10,
                               retries_sleep=60, queue_derive=False, verify=True, verbose=True, )
        responses.append(response)
        url_to_status_code = \
            {r.request.url: r.status_code for r in response}
        book.logger.debug('Response from upload: {} | {}'
                          .format(response, url_to_status_code))

    return book_preimage_upload_start, book_preimage_upload_end, sizes_dict

def _upload_logs( book, item, responses):
    book.update_message('Upload | Logs')
    if os.path.exists(os.path.join(book['path'], 'iabdash.log')):
        book.logger.debug(
            'Uploading iabdash events log file'
        )
        upload_name_mapping = \
            {'logs/' + book['identifier']
             + '_iabdash_{:%Y-%m-%d%H:%M:%S}.log'.format(datetime.now()):
                 join(book['path'], 'iabdash.log')}
        response = item.upload(upload_name_mapping, retries=10,
                               retries_sleep=60, queue_derive=False, verify=True, verbose=True, )
        responses.append(response)
        url_to_status_code = \
            {r.request.url: r.status_code for r in response}
        book.logger.debug('Response from upload: {} | {}'
                          .format(response, url_to_status_code))

    if os.path.exists(book.STATUS_HISTORY_FILE):
        book.logger.debug(
            'Uploading status history log file'
        )
        upload_name_mapping = \
            {'logs/' + book['identifier']
             + '_status_history_{:%Y-%m-%d%H:%M:%S}.log'.format(datetime.now()):
                 book.STATUS_HISTORY_FILE}
        response = item.upload(upload_name_mapping, retries=10,
                               retries_sleep=60, queue_derive=False, verify=True, verbose=True, )
        responses.append(response)
        url_to_status_code = \
            {r.request.url: r.status_code for r in response}
        book.logger.debug('Response from upload: {} | {}'
                          .format(response, url_to_status_code))

    if os.path.exists(os.path.join(book['path'], 'scanning.log')):
        book.logger.debug(
            'Uploading Scanning log file'
        )
        upload_name_mapping = \
            {'logs/' + book['identifier']
             + '_scanning_{:%Y-%m-%d%H:%M:%S}.log'.format(datetime.now()):
                 join(book['path'], 'scanning.log')}
        response = item.upload(upload_name_mapping, retries=10,
                               retries_sleep=60, queue_derive=False, verify=True, verbose=True, )
        responses.append(response)
        url_to_status_code = \
            {r.request.url: r.status_code for r in response}
        book.logger.debug('Response from upload: {} | {}'
                          .format(response, url_to_status_code))


def _generate_metasource(book, Logger):
    # Upload a metasource.xml
    metasource_file_location = ''
    metasource = get_metadata(book['path'], 'metasource.xml')
    # if there is a metasource file present, add upload-time fields
    if metasource != {}:
        metasource['textid'] = book['identifier']
        metasource['userid'] = _get_email()
        metasource['date'] = datetime.now().strftime('%Y%m%d%H%M%S')
        set_metadata(metasource, book['path'],
                     'metasource.xml', 'metasource')
        metasource_file_location = join(book['path'], 'metasource.xml')
        metasource_file_upload_name = \
            book['identifier'] + '_metasource.xml'
        Logger.debug('Written metasource file at {}'
                          .format(metasource_file_location))
        return metasource_file_location, metasource_file_upload_name
    else:
        return None, None

def _fill_metadata(scancenter_md,collections_list, item, md, Logger, override=False):
    Logger.debug('upload_book: fusing metadata')

    if item.exists and not override:
        scancenter_md_clean = {}
        Logger.debug('upload_book: Item exists already, '
                     'pushing selective metadata')
        for k in list(scancenter_md.keys()):
            if k in ['scanner', 'operator', 'tts_version']:
                if scancenter_md[k] != '':
                    scancenter_md_clean[k] = scancenter_md[k]

        # in case the item exists, use the collection settings from
        # Archive
        #
        # md['collection'] = item.metadata['collection']
        # md.update(scancenter_md_clean)
        if 'notes' in md:
            scancenter_md_clean['notes'] = md['notes']

        if 'source' in md:
            scancenter_md_clean['source'] = md['source']

        if 'camera' in md:
            scancenter_md_clean['camera'] = md['camera']

        if 'boxid' in md:
            scancenter_md_clean['boxid'] = md['boxid']

        md = scancenter_md_clean
    else:
        Logger.debug('upload_book: Item does not exist. '
                     'Pushing ALL metadata.')
        for entry in ['language', 'scanner', 'tts_version']:
            if entry not in md:
                md[entry] = scancenter_md[entry]
        # Otherwise, if it's a new item, get the collection from the
        # item's metadata
        #
        # if scancenter_md['collection'] is None:
        try:
            md['collection'] = collections_list
        except Exception:
            # if this fails, it means that there is no collection
            # information in the item's metadata.
            Logger.exception('upload_book: No collection set '
                             'information found')
            collections_list = []

    return md


def _prepare_metadata(book, item, Logger, override=False):
    md = get_metadata(book['path'])
    send_to_station_file = os.path.join(book['path'], 'send_to_station')
    if os.path.exists(send_to_station_file):
        md['repub_state'] = '40'
    else:
        md['repub_state'] = '10'
    md['mediatype'] = 'texts'

    for k, v in md.items():
        if ';' in v and k in scribe_globals.FLAT_MD_FIELDS:
            Logger.info('Detected a list-like flat field;'
                             'converting {} ({})to list.'.format(k, v))
            md[k] = v.split(';')

    try:
        collections_list = md['collection']
    except Exception:
        Logger.exception('upload_book: Could not find collection or '
                         'collection set specification in book '
                         'metadata.')
        collections_list = []

    scancenter_md = get_sc_metadata()

    # we assume operator is the one provided by the machine
    # but we honor what has been set upstream
    if 'operator' in md:
        scancenter_md['operator'] = md['operator']

    # same for language
    if 'language' in md:
        scancenter_md['language'] = md['language']

    filled_md = _fill_metadata(scancenter_md, collections_list, item, md,  Logger, override)

    # The old Scribe software uses author instead of creator, so we
    # do too, but we need to change this on upload
    if 'author' in filled_md:
        Logger.debug('upload_book: Converting author field to creator '
                     'before upload to cluster')
        filled_md['creator'] = md['author']
        del filled_md['author']

    if 'identifier' not in filled_md:
        filled_md['identifier'] = item.identifier

    if config.is_true('set_noindex'):
        filled_md['noindex'] = 'true'

    encoded_md = _clean_metadata(filled_md, Logger)
    return encoded_md


def _clean_metadata(md, Logger):
    encoded_md = {}
    for entry in md.items():
        try:
            k, v = entry
        except:
            Logger.error('MD field {} empty - ignoring'.format(entry))
            continue
        encoded_md[k] = v
    return encoded_md

def _check_repub_state_is_correct(item):
    if not item.exists:
        return

    if item.metadata['mediatype'] == 'audio':
        return

    if item.metadata['repub_state'] not in ['-1', '-2', ]:
        raise ScribeException('Book is not in correct remote repub_state '
                              '(is {}): aborting upload.'.format(
                                            item.metadata['repub_state']))

def _check_remote_preconditons(book_item, Logger):
    _check_repub_state_is_correct(book_item)

    identifier = book_item.identifier

    outstanding_catalog_tasks, outstanding_catalog_tasks_list = get_pending_catalog_tasks(identifier)

    if outstanding_catalog_tasks > 0:
        msg = 'Refusing to upload: item {} has {} outstanding (running or pending) catalog book_tasks\n{}'.format(
            book_item.identifier,
            outstanding_catalog_tasks,
            ', '.join(
                ['{} -> {} ({})'.format(
                    x['task_id'], x['cmd'], x['status'])
                    for x in outstanding_catalog_tasks_list])
        )
        Logger.error(msg)
        raise Exception(msg)

def _check_preconditons(book):
    if book['status'] >= UploadStatus.uploaded.value:
        raise Exception('This function cannot be used on downloaded items.')

def _check_preimage_is_valid(book):
    zip_path = (
        join(book['path'],
             '{id}_preimage.zip'.format(id=book['identifier']))
    )

    if not os.path.exists(zip_path):
        raise ScribeException('Could not find preimage.zip in book folder.')
    elif os.path.getsize(zip_path) <= 532:  # size of an empty zip
        raise ScribeException('preimage.zip is zero length!')
    return zip_path

def _only_push_metadata(encoded_md, book, item, responses, Logger,):
    if os.path.exists(os.path.join(book['path'], 'send_to_station')):
        encoded_md['repub_state'] = '40'
    else:
        encoded_md['repub_state'] = '10'
    
    Logger.debug('upload_book: Since the item already exists, '
                 'only pushing this metadata: {}'
                 .format(encoded_md))

    response = item.modify_metadata(encoded_md)

    if response.status_code == 200:
        responses.append([response])

    elif response.status_code == 400:
        if 'no changes to _meta.xml' in response.text:
            response.status_code = 499
            responses.append([response])
        else:
            raise Exception('Response code {} {} - {} from metadata API. '
                            'URL was: {} | content: {}'
                            'This was not a "no changes in _meta.xml" error.'
                            'Aborting upload of preloaded item {}'.
                            format(response.status_code,
                                   response.reason,
                                   response.text if 'text' in response else "",
                                   response.url,
                                   response.content,
                                   item.identifier))
    else:
        raise Exception('Response code {} {} - {} from metadata API. '
                        'URL was: {} | content: {}'
                        'Aborting upload of preloaded item {}'.
                        format(response.status_code,
                               response.reason,
                               response.text if 'text' in response else "",
                               response.url,
                               response.content,
                               item.identifier))

def upload_book(book):
    Logger = book.logger
    Logger.debug('Starting upload of ' + book['identifier'])

    _check_preconditons(book)

    #book.do_book_upload_begin()

    _set_upload_lock_file(book, Logger)

    responses_dict = {}
    book_upload_total_start = time.time()
    try:
        scandata = ScanData(book['path'])

        zip_path = _check_preimage_is_valid(book)

        ia_session = get_ia_session()
        item = ia_session.get_item(book['identifier'])
        Logger.info('Got item {}'.format(item.identifier))

        if not book.force_upload:
            _check_remote_preconditons(item, Logger)

        encoded_md = _prepare_metadata(book, item, Logger)

        metasource_file_location, metasource_file_upload_name = _generate_metasource(book, Logger)

        responses = []
        book_upload_phase_start = time.time()

        needs_metadata_pushed = item.exists

        doing_foldouts = os.path.exists(os.path.join(book['path'], 'send_to_station'))

        book_preimage_upload_start, \
        book_preimage_upload_end, \
        sizes_dict                  = _upload_book_files( zip_path, book,
                                                        encoded_md, item, responses,
                                                        metasource_file_location,
                                                        metasource_file_upload_name,
                                                        Logger)

        if needs_metadata_pushed:
            _only_push_metadata(encoded_md, book, item, responses, Logger)

        book_upload_phase_end = time.time()

        _upload_logs(book=book, item=item, responses=responses)

        _verify_responses(responses, Logger)

        Logger.debug('OK! Finished uploads to {} | Took {}s'
                          .format(book['identifier'],
                                  book_upload_phase_end - book_upload_phase_start))

        book.do_upload_book_end()

        _push_metrics(book, scandata, encoded_md, sizes_dict, doing_foldouts,
                      responses, responses_dict, book_upload_phase_start,
                      book_upload_phase_end, book_upload_total_start,
                      book_preimage_upload_start, book_preimage_upload_end)

        if config.is_true('show_book_notifications'):
            notifications_manager.add_notification(title='Uploaded',
                                               message="{} has been successfully uploaded.".format(
                                                   book['identifier']),
                                               book=book)

        Logger.debug('Finished upload for ' + book['identifier'])

        # Clock.schedule_once(partial(self.update_status_callback, book))
        time.sleep(10)  # Wait for book to be added to metadata api
    except requests.ConnectionError as e:

        book.do_upload_book_error()
        Logger.error(traceback.format_exc())
        payload = {'local_id': book['uuid'],
                   'status': book['status'],
                   'exception': str(e)}

        push_event('tts-book-failed-upload', payload,
                   'book', book['identifier'])


        raise ScribeException('Upload Failed. '
                              'Please check network and S3 Keys')
    except Exception as e:

        book.do_upload_book_error()
        Logger.error(traceback.format_exc())

        payload = {'local_id': book['uuid'],
                   'status': book['status'],
                   'responses': responses_dict,
                   'exception': str(e)}

        push_event('tts-book-upload-exception', payload,
                   'book', book['identifier'])

        raise ScribeException('Upload Failed! - {}'.format(str(e)))
    finally:
        book.force_upload = False
        Logger.info("Removing upload lock file at {}".format(join(book['path'], "upload_lock")))
        os.remove(join(book['path'], "upload_lock"))


def random_string():
    '''
    from TextsRemote::random_string()

    >>> s = random_string()
    >>> m = re.findall('^[a-z]\d[a-z]\d$', s)
    >>> m == [s]
    True
    '''

    random_str = ''.join([random.choice(string.ascii_lowercase),
                          random.choice(string.digits),
                          random.choice(string.ascii_lowercase),
                          random.choice(string.digits)])
    return random_str


def purify_string(s):
    '''
    From BiblioString::purify_string()

    >>> purify_stri ng('THE UPPER And the lower')
    'upperlower'
    '''
    patterns = ('^a\s+','^an\s+','^the\s+',
                '\sa\s','\san\s',
                '\sand\sthe\s','\sand\s','\sthe\s',
                '\s+',
                '\!','\@','\#','\$','\%','\^',
                '\&','\*','\(','\)','\+','\=',
                '\{','\}','\[','\]','\|','\\\\',
                '\:','\;','\'','\"',
                '\<','\>','\,','\?','\/',
                '\.','\-',
                '~/',
                'electronic.*resource','microform',
                'microfilm',
                '[^a-zA-Z0-9\.\-_]+', #strip non-ascii
               )
    s = s.lower()
    for p in patterns:
        s = re.sub(p, '', s)

    if s == '':
        s = 'unset'
    return s


def id_available(identifier):
    '''
    Query the upload_api to see if an identifier is available.
    '''
    try:
        url = 'https://archive.org/upload/app/upload_api.php'
        params = {'name':'identifierAvailable', 'identifier':identifier}
        r = requests.get(url, params=params)
        ret = r.json()
        success = ret.get('success', False)
    except Exception:
        print((traceback.format_exc()))
        raise ScribeException('Could not query upload_api for identifierAvailable')

    if success == False:
        return False
    return True
    
