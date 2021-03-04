import base64
import os
from os.path import join

import json
import requests

from ia_scribe import scribe_globals
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.book.metadata import get_metadata, set_metadata
from ia_scribe.tasks.task_base import TaskBase
from ia_scribe.tasks.ia_identifier import MakeIdentifierTask
from ia_scribe.ia_services.btserver import get_ia_session
from ia_scribe.ia_services.iabdash import push_event
from ia_scribe.ia_services.ingestion_adapters import put_metric
from ia_scribe.utils import get_string_value_if_list, \
    ensure_book_directory
from ia_scribe.tasks.book_tasks.identifier import make_identifier

config = Scribe3Configuration()

ALLOWED_FORMATS = {
    'Metadata', 'MARC', 'MARC Source', 'MARC Binary', 'Dublin Core',
    'Archive BitTorrent', 'Web ARChive GZ', 'Web ARChive', 'Log',
    'OCLC xISBN JSON', 'Internet Archive ARC', 'Internet Archive ARC GZ',
    'CDX Index', 'Item CDX Index', 'Item CDX Meta-Index', 'WARC CDX Index',
    'Metadata Log',
}

ALLOWED_FILE_NAMES = {
    '__ia_thumb.jpg',
}

ALLOWED_VARIABLE_FILE_NAMES = {
    'events.json', 'loans.json', 'extrameta.json',
    'slip.png', 'slip_thumb.jpg',
    'bhlmets.xml', 'bhlmets.xml_meta.txt',
    'names.xml', 'names.xml_meta.txt',
}

class MetadataViaIdentifierTask(TaskBase):

    _url = 'https://archive.org/metadata/{identifier}/files'
    _metadata_url = 'https://archive.org/download/' \
                    '{identifier}/{identifier}_meta.xml'

    def __init__(self, **kwargs):
        super(MetadataViaIdentifierTask, self).__init__(logger=kwargs['book'].logger, **kwargs)
        self.book = kwargs['book']
        self.book_path = self.book.path
        self.identifier = kwargs['identifier']
        self._ia_item = None
        self._should_delete_book = False
        self._metadata_load_failed = False

    def create_pipeline(self):
        return [
            self._ensure_book_directory,
            self._download_metadata_files_list,
            self._download_ia_item,
            self._download_metadata_xml_file,
            self._write_identifier_and_preloaded_file,
            self._change_book_state,
            self._refresh_book,
            self._update_repub_state,
            self._notify_iabdash,
        ]

    def should_delete_book(self):
        return self._should_delete_book

    def is_metadata_load_failed(self):
        return self._metadata_load_failed

    def _ensure_book_directory(self):
        self.dispatch_progress('Ensuring that book directory exists')
        ensure_book_directory(self.book_path)

    def _download_metadata_files_list(self):
        self.dispatch_progress('Downloading metadata files list')
        url = self._url.format(identifier=self.identifier)
        try:
            result = requests.get(url).json()
        except Exception:
            self._metadata_load_failed = True
            raise
        error_message = self._validate_metadata_files(result)
        if error_message:
            self.error = ValueError(error_message)

    def _validate_metadata_files(self, files):
        self.dispatch_progress('Validating downloaded metadata files')
        if files is None:
            return 'Could not fetch metadata from archive.org'
        elif 'error' in files:
            return files['error']
        elif 'result' not in files:
            return 'archive.org Metadata API returned an empty response'
        else:
            #prepare candidate filenames
            ALLOWED_ITEM_FILE_NAMES = [ '{}_{}'.format(self.identifier, x)
                                        for x in ALLOWED_VARIABLE_FILE_NAMES]

            for file_metadata in files['result']:
                if file_metadata['format'] not in ALLOWED_FORMATS:
                    # Ignore new style in-item thumb files
                    if file_metadata['name'] in ALLOWED_FILE_NAMES:
                        continue
                    if file_metadata['name'] in ALLOWED_ITEM_FILE_NAMES:
                        continue
                    message = (
                        'This item already contains data files!'
                        '\nFile {file} ({format})'
                        .format(file=file_metadata['name'], format=file_metadata['format'])
                    )
                    return message
        return None

    def _download_ia_item(self):
        self.dispatch_progress('Downloading ia item')
        session = get_ia_session()
        self._ia_item = session.get_item(self.identifier)
        error_message = self._validate_ia_item()
        if error_message:
            self._should_delete_book = False
            self.error = ValueError(error_message)

    def _validate_ia_item(self):
        item = self._ia_item
        self.dispatch_progress('Validating ia item')
        if item.metadata['repub_state'] != '-1':
            message = 'This identifier has already been claimed and ' \
                      'its repub_state is [b]{}[/b].' \
                .format(item.metadata['repub_state'])
            if 'scandate' in item.metadata:
                message += '\nIt was scanned on {}' \
                    .format(item.metadata['scandate'])
            if 'scanner' in item.metadata:
                message += '\nIt was scanned by {}' \
                    .format(item.metadata['scanner'])
            message += '\n\nIf you need to use this identifier, please notify your Supervisor ' \
                       'to verify its eligibility, as the book\'s repub_state will need ' \
                       'to be reset to -1, and uploaded images/files may need to be gutted.'
            return message
        return None

    def _download_metadata_xml_file(self):
        self.dispatch_progress('Downloading metadata.xml')
        metadata_path = join(self.book_path, 'metadata.xml')
        url = self._metadata_url.format(identifier=self.identifier)
        response = requests.get(url, stream=True)
        self.dispatch_progress('Saving metadata.xml to disk')
        with open(metadata_path, 'wb') as fd:
            for chunk in response.iter_content(chunk_size=128):
                fd.write(chunk)
        metadata = self._safe_load_metadata()
        if not metadata:
            error_message = 'Malformed metadata.xml pulled from cluster. ' \
                            'Now removing, please retry!'
            self.error = ValueError(error_message)
            os.remove(metadata_path)

    def _write_identifier_and_preloaded_file(self):
        identifier_path = join(self.book_path, 'identifier.txt')
        with open(identifier_path, 'w+') as f:
            f.write(self.identifier)
        preloaded_path = join(self.book_path, 'preloaded')
        open(preloaded_path, 'w').close()

    def _update_repub_state(self):
        state = -2
        errors = []
        self.dispatch_progress('Setting republisher state to {}'.format(state))
        for _ in range(scribe_globals.TASK_DEFAULT_MAX_RETRIES):
            try:
                self.dispatch_progress('[{}/{}] Setting republisher state to {}'
                                       .format( _+1, scribe_globals.TASK_DEFAULT_MAX_RETRIES, state))
                ia_item = get_ia_session().get_item(self.identifier)
                resp = ia_item.modify_metadata({'repub_state': state})
                self.logger.info('Response from cluster: {} | '
                                 'Headers {}'.format(resp.text, resp.headers))
            except Exception as e:
                self.logger.error('[{}/{}] Transient error {} while setting repub_state to {}.'
                                  .format( _ +1 , scribe_globals.TASK_DEFAULT_MAX_RETRIES, e, state))
                errors.append(e)
                continue
            else:
                break
        else:
            self.logger.error('Could not set repub_state to {} because {}'
                              .format(state, errors[-1]))
            payload = {'task_type': 'MetadataViaIdentifierTask',
                       'selector': self.identifier,
                       'type': 'identifier',
                       'errors': json.dumps([str(x) for x in errors]),
                       'attempts': len(errors),
                       }

            push_event('tts-task-exception', payload)
            raise errors[-1]

    def _notify_iabdash(self):
        self.dispatch_progress('Notifying iabdash')
        payload = {'task_type': 'MetadataViaIdentifierTask',
                   'selector': self.identifier,
                   'type': 'identifier',
                   }
        try:
            push_event('tts-task-success', payload)
            self.logger.info('MetadataViaIdentifierTask: Pushed event tts-task-success to '
                        'iabdash with payload: {}'.format(payload))
        except Exception:
            self.logger.exception('MetadataViaIdentifierTask: Failed to push tts-task-success '
                             'event with payload: {}'.format(payload))

    def _safe_load_metadata(self):
        # TODO: Validate downloaded metadata
        try:
            return get_metadata(self.book_path)
        except Exception:
            return None

    def _change_book_state(self):
        self.dispatch_progress('Transitioning state to identifier_assigned')
        self.book.do_create_identifier()

    def _refresh_book(self):
        self.dispatch_progress('Reloading metadata')
        self.book.reload_metadata()


class LiteMetadataViaIdentifierTask(MetadataViaIdentifierTask):


    def _validate_metadata_files(self, files):
        self.dispatch_progress('Validating downloaded metadata files')
        if files is None:
            return 'Could not fetch metadata from archive.org'
        elif 'error' in files:
            return files['error']
        elif 'result' not in files:
            return 'archive.org Metadata API returned an empty response'
        return None

    def _validate_ia_item(self):
        msg = 'Ignoring ia item validation'
        self.dispatch_progress(msg)
        self.logger.info(msg)

    def _update_repub_state(self):
        msg = 'Ignoring repub state update'
        self.dispatch_progress(msg)
        self.logger.info(msg)


class MetadataViaISBNTask(TaskBase):

    _url = 'https://archive.org/book/want/isbn_to_identifier.php?isbn={isbn}'

    def __init__(self, **kwargs):
        super(MetadataViaISBNTask, self).__init__(**kwargs)
        self.isbn = kwargs['isbn']
        self.archive_ids = None
        self._should_select_identifier = False

    def should_select_identifier(self):
        return self._should_select_identifier

    def create_pipeline(self):
        return [self._load_identifiers]

    def _load_identifiers(self):
        error = None
        self.dispatch_progress('Loading scannable identifiers')
        try:
            url = self._url.format(isbn=self.isbn)
            response = requests.get(url)
            if response.status_code != 200:
                error = ValueError(response.text)
            else:
                payload = response.json()
                if payload['status'] == 'ok':
                    self.archive_ids = list(payload['scannable_identifiers'])
                    self._should_select_identifier = True
                else:
                    self._should_start_dwwi_search = True
        except Exception as e:
            message = 'Could not retrieve ISBN.\nCheck the console log for ' \
                      'more information.\n\nError type: {0}'.format(type(e))
            error = ValueError(message)
        if error:
            raise error


class MARCMetadataViaDWWITask(TaskBase):

    _url = 'https://archive.org/book/marc/' \
           'get_any_marc.php?isbn={isbn}'

    def __init__(self, **kwargs):
        super(MARCMetadataViaDWWITask, self).__init__(**kwargs)
        self.book_path = kwargs['book_path']
        self.isbn = kwargs['isbn']
        self.extra = kwargs['extra']
        self.volume = kwargs.get('volume', None)
        self.identifier = None
        self.metadata = None
        self.marc_download_failed = False
        self._marc_response = None

    def create_pipeline(self):
        return [
            self._ensure_book_directory,
            self._save_original_isbn_to_file,
            self._download_marc_response,
            self._handle_marc_response,
            self._update_set_book_repub_state,
            self._notify_iabdash,
        ]

    def _save_original_isbn_to_file(self):
        self.dispatch_progress('Storing original ISBN')
        target = os.path.join(self.book_path, scribe_globals.ORIGINAL_ISBN_FILENAME)
        with open(target, 'w+') as f:
            f.write(self.isbn)

    def _ensure_book_directory(self):
        self.dispatch_progress('Ensuring that book directory exists')
        ensure_book_directory(self.book_path)

    def _download_marc_response(self):
        self.dispatch_progress('Downloading marc record')
        url = self._url.format(isbn=self.isbn)
        self._marc_response = requests.get(url).json(encoding='utf-8')

    def _handle_marc_response(self):
        progress = self.dispatch_progress
        response = self._marc_response
        book_path = self.book_path
        if response['sts'] == 'OK':
            progress('Found MARC data for this book. Writing MARCXML')
            with open(join(book_path, 'marc.xml'), 'w+') as fd:
                fd.write(response['marc_xml'].encode('utf-8'))
            progress('Writing MARC binary')
            with open(join(book_path, 'marc.bin'), 'wb+') as fd:
                marcbin = bytes(response['marc_binary'].encode('utf-8'))
                fd.write(marcbin)
            self.metadata = md = response['extracted_metadata']['metadata']
            for key in list(md.keys()):
                if self.metadata[key] in ['', None]:
                    self.metadata.pop(key)
            for key, value in self.metadata.items():
                if type(value) is dict:
                    dict_as_list = list(value.values())
                    self.metadata[key] = dict_as_list
            if 'isbn' in self.metadata:
                if self.metadata['isbn'] in [None, 'None']:
                    self.metadata['isbn'] = '{}'.format(self.isbn)
                elif type(self.metadata['isbn']) == list:
                    if self.isbn not in self.metadata['isbn']:
                        self.metadata['isbn'].append(self.isbn)
                elif type(self.metadata['isbn']) == str:
                    self.metadata['isbn'] = [self.metadata['isbn'], self.isbn]
            else:
                self.metadata['isbn'] = '{}'.format(self.isbn)
            if self.volume:
                self.metadata['volume'] = self.volume
            if self.extra:
                for field in ['boxid', 'old_pallet']:
                    value = [x['value'] for x in self.extra if x['key'] == field][0]
                    self.metadata[field] = value
            progress('Saving metadata')
            # TODO: Regression: Only metadata from form should be saved?
            # Check CaptureScreen.download_and_save_marc method
            set_metadata(self.metadata, book_path)
            progress('Creating new identifier')
            self.identifier = identifier = make_identifier(
                title=self.metadata.get('title', None) or 'unset',
                volume=self.metadata.get('volume', None) or '00',
                creator=get_string_value_if_list(self.metadata, 'creator') or 'unset'
            )
            progress('Setting identifier to {}'.format(identifier))
            with open(join(book_path, 'identifier.txt'), 'w') as fd:
                fd.write(identifier)
        else:
            self.marc_download_failed = True
            self.identifier = identifier = 'isbn_' + self.isbn
            if self.volume and self.volume != '0':
                self.identifier = identifier = 'isbn_{}_{}'.format(self.isbn,
                                                                   self.volume)
            progress('No MARC record found for this book. '
                     'Setting identifier to {}'.format(identifier))
            with open(join(book_path, 'identifier.txt'), 'w+') as fd:
                fd.write(identifier)
            with open(join(book_path, scribe_globals.ORIGINAL_ISBN_FILENAME), 'w+') as fd:
                fd.write(self.isbn)

    def _update_set_book_repub_state(self):
        state = -2
        errors = []
        self.dispatch_progress('Setting republisher state to {}'.format(state))
        for _ in range(scribe_globals.TASK_DEFAULT_MAX_RETRIES):
            try:
                self.dispatch_progress(
                    '[{}/{}] Setting republisher state to {}'.format(_ + 1, scribe_globals.TASK_DEFAULT_MAX_RETRIES,
                                                                     state))
                ia_item = get_ia_session().get_item(self.identifier)
                resp = ia_item.modify_metadata({'repub_state': state})
                self.logger.info('Response from cluster: {} | '
                                 'Headers {}'.format(resp.text, resp.headers))
            except Exception as e:
                self.logger.error('[{}/{}]Transient error {} while setting repub_state to {}.'
                                  .format( _+1, scribe_globals.TASK_DEFAULT_MAX_RETRIES, e, state))
                errors.append(e)
                continue
            else:
                break
        else:
            self.logger.error('Could not set repub_state to {} because {}'
                              .format(state, errors[-1]))
            payload = {'task_type': 'MARCMetadataViaDWWITask',
                       'selector': self.isbn,
                       'type': 'isbn',
                       'errors': json.dumps([str(x) for x in errors]),
                       'attempts': len(errors),
                       }

            push_event('tts-task-exception', payload)

            #raise errors[-1]

    def _notify_iabdash(self):
        self.dispatch_progress('Notifying iabdash')
        payload = {'task_type': 'MARCMetadataViaDWWITask',
                   'selector': self.identifier,
                   'type': 'identifier',
                   }
        try:
            push_event('tts-task-success', payload)
            put_metric('scribe3.tasks.metadata.dwwi', '1' , payload)
            self.logger.info('MARCMetadataViaDWWITask: Pushed event tts-task-success to '
                        'iabdash with payload: {}'.format(payload))
        except Exception:
            self.logger.exception('MARCMetadataViaDWWITask: Failed to push tts-task-success '
                             'event with payload: {}'.format(payload))


class DeferredMetadataViaWonderfetch(TaskBase):

    def __init__(self, **kwargs):
        self.book = kwargs['book']
        self.search_id = None
        self.search_method = None
        self.search_catalog = None
        self.result = None
        self.payload = None
        self._initial_metadata = self.book.metadata
        self.user_input = None
        self.md_task = MetadataViaOpenlibraryTask(book=self.book,
                                   payload=self.payload,
                                   search_id=self.search_id,
                                   volume=self.book.metadata.get('volume'),
                                   extra={},

                                   )
        super(DeferredMetadataViaWonderfetch, self).__init__(logger=kwargs['book'].logger, **kwargs)

    def _handle_sub_task_error(self, sub_task, index, error):
        return False

    def create_pipeline(self):
        return [
            self._load_search_selectors,
            self._retrieve_data,
            self._validate_search,
            self._setup_md_task,
            self.md_task,
            self._change_state,
        ]

    def _load_search_selectors(self):
        from ia_scribe.uix.widgets.wonderfetch.wonderfetch_widget import DEFAULT_CATALOG
        self.dispatch_progress('Loading selectors')
        self.search_id = self.book.metadata.get('scribe3_search_id')
        self.search_method = self.book.metadata.get('scribe3_search_method')
        self.search_catalog = self.book.metadata.get('scribe3_search_catalog', DEFAULT_CATALOG)
        if self.search_id in [None, '']:
            raise Exception('Cannot find a valid search_id.')
        if self.search_method in [None, '']:
            raise Exception('Cannot find a valid search method.')
        if self.search_catalog in [None, '']:
            raise Exception('Cannot find a valid search catalog.')

    def _retrieve_data(self):
        self.dispatch_progress('Pulling data')
        from ia_scribe.uix.widgets.wonderfetch.wonderfetch_backend import get_api_result
        self.result, self.payload = get_api_result(self.search_method,
                                                   self.search_id,
                                                   catalog=self.search_catalog)

    def _validate_search(self):
        self.dispatch_progress('Validating data')
        condition = self.result \
                    and self.payload.get('status') == 'ok' \
                    and 'invalid' not in self.payload.get('message')
        if not condition:
            if not self.user_input:
                self.pause()
                popup_msg = ('The API response was empty or invalid.\n\n'
                              'If you continue, an item with no metadata will be created,'
                              'and its identifer will be in the form unset0000unset. '
                              'Would you like to abort?'
                             )
                # Flag progress report that user input is need for task to
                # continue. Keyword `input_needed` is arbitrary
                self.dispatch_progress('Step %s' % self._current_index,
                                       task=self,
                                       input_needed=True,
                                       title='API Error',
                                       input_type = 'yes_no_decision',
                                       popup_body_message=popup_msg)
                self._stay_on_current_step = True
            else:
                self.dispatch_progress('Step %s: User input: %s'
                                       % (self._current_index, self.user_input))
                self._stay_on_current_step = False
                if self.user_input == 'yes':
                    raise Exception('You have elected not to try again'
                                    '\nTask terminated.')
                else:
                    self.user_input = None
                    self.logger.info('User elected to try again with selector {}'.format(self.search_id))

    def _setup_md_task(self):
        self.dispatch_progress('Saving data')
        #self.md_task.reset()
        self.payload['scribe3_search_catalog'] = self.search_catalog
        self.md_task.payload = self.payload
        self.md_task.search_id = self.search_id


    def _change_state(self):
        self.book.do_deferred_load_metadata()

class MetadataViaOpenlibraryTask(TaskBase):

    def __init__(self, **kwargs):
        self.book = kwargs['book']
        self.search_id = kwargs['search_id']
        self.extra = kwargs['extra']
        self.payload = kwargs['payload']
        self.volume = kwargs.get('volume', None)
        self.selector = None
        self.marc_download_failed = False
        self._raw_response = None
        self.metadata = None
        super(MetadataViaOpenlibraryTask, self).__init__(logger=kwargs['book'].logger, **kwargs)

    def create_pipeline(self):
        return [
            self._retrieve_data,
            self._handle_marc_response,
            self._reload_book_metadata,
            MakeIdentifierTask(book=self.book),
            self._notify_iabdash,
        ]

    def _retrieve_data(self):
        self.dispatch_progress('Pulling data')
        self._raw_response = self.payload
        self._marc_response = self._raw_response['marc_data']

    def _handle_marc_response(self):
        progress = self.dispatch_progress
        progress('Handling MARC data')
        response = self._marc_response
        book_path = self.book.path
        if len(response)>0 and response['sts'] == 'OK':
            progress('Found MARC data for this book. Writing MARCXML')
            with open(join(book_path, 'marc.xml'), 'w+') as fd:
                fd.write(self._marc_response['marc_xml'])
            progress('Writing MARC binary')
            with open(join(book_path, 'marc.bin'), 'wb+') as fd:
                base64_encoded_marc = self._marc_response['marc_binary']
                decoded_marc = base64.b64decode(base64_encoded_marc)
                fd.write(decoded_marc)
            progress('Extracting metadata')
            self.metadata = self._marc_response['extracted_metadata']['metadata']
            progress('Mangling metadata')
            self.metadata = md = response['extracted_metadata']['metadata']
            for key in list(md.keys()):
                if self.metadata[key] in ['', None]:
                    self.metadata.pop(key)
            for key, value in self.metadata.items():
                if type(value) is dict:
                    dict_as_list = list(value.values())
                    self.metadata[key] = dict_as_list
            if self.volume:
                self.metadata['volume'] = self.volume
            if self.extra:
                for field in ['boxid', 'old_pallet']:
                    value = [x['value'] for x in self.extra if x['key'] == field][0]
                    self.metadata[field] = value
            self.metadata['scribe3_search_id'] = '{}'.format(self.search_id)
            self.metadata['scribe3_search_catalog'] = '{}'.format(self.payload.get('scribe3_search_catalog'))
            # These rely on upstream OL specs and we can't trust them 100%
            try:
                if self.payload.get('olid', None):
                    self.metadata['openlibrary_edition'] = '{}'.format(self.payload.get('olid'))
                self.metadata['openlibrary_work'] = '{}'.format(self.payload['ol_data']['details']['works'][0]['key'])
            except Exception as e:
                print('MetadataViaOpenlibraryTask: failed to retrieve ol data with error {}'.format(e))
                pass
        else:
            self.marc_download_failed = True
            self.metadata = {}
            self.metadata['scribe3_search_id'] = '{}'.format(self.search_id)
            self.metadata['scribe3_search_catalog'] = '{}'.format(self.payload.get('scribe3_search_catalog'))

            if self.extra:
                for field in ['boxid', 'old_pallet']:
                    value = [x['value'] for x in self.extra if x['key'] == field][0]
                    self.metadata[field] = value

            if self.volume:
                self.metadata['volume'] = self.volume

            with open(join(book_path, scribe_globals.ORIGINAL_ISBN_FILENAME), 'w+') as fd:
                fd.write(self.search_id)

        self.metadata['operator'] = self.book.operator
        self.metadata['scanningcenter'] = self.book.scanningcenter
        progress('Saving metadata')
        set_metadata(self.metadata, book_path)

    def _reload_book_metadata(self):
        self.dispatch_progress('Reloading book metadata')
        self.book.reload_metadata()

    def _notify_iabdash(self):
        self.dispatch_progress('Notifying iabdash')
        payload = {'task_type': 'MARCMetadataViaDWWITask',
                   'search_id': self.metadata['scribe3_search_id'],
                   'catalog': self.metadata['scribe3_search_catalog'],
                   'identifier': self.book.identifier,
                   }
        try:
            push_event('tts-task-success', payload)
            put_metric('scribe3.tasks.metadata.dwwi', '1' , payload)
            self.logger.info('MARCMetadataViaDWWITask: Pushed event tts-task-success to '
                        'iabdash with payload: {}'.format(payload))
        except Exception:
            self.logger.exception('MARCMetadataViaDWWITask: Failed to push tts-task-success '
                             'event with payload: {}'.format(payload))

