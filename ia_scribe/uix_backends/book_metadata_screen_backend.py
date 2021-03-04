import os, datetime, time
from copy import copy, deepcopy
from itertools import groupby
from operator import itemgetter
from os.path import exists, join, basename
from pprint import pformat
from uuid import uuid4

from kivy.logger import Logger
from kivy.properties import NumericProperty

from ia_scribe import scribe_globals
from ia_scribe.ia_services.iabdash import push_event

from ia_scribe.config.config import Scribe3Configuration

from ia_scribe.book.library import Library
from ia_scribe.book.book import (
    ensure_book_directory,
    ST_HAS_IDENTIFIER,
    ST_DOWNLOADED,
    ST_PRELOADED,
    ST_HAS_MARC_BIN,
    ST_HAS_MARC_XML,
    ST_HAS_METASOURCE,
    ST_QUEUED_FOR_DELETE
)
from ia_scribe.book.metadata import (
    MD_READONLY_KEYS,
    MD_REQUIRED_KEYS,
    MD_ORDERED_KEYS,
    MD_NEW_BOOK_KEYS,
    MD_KEYS_WITH_SINGLE_VALUE,
    get_metadata,
    set_metadata,
    get_sc_metadata
)
from ia_scribe.scribe_globals import CONFIG_DIR, BOOKS_DIR, DEFAULT_PPI
from ia_scribe.tasks.metadata import (
    MetadataViaIdentifierTask,
    MetadataViaOpenlibraryTask,
    MetadataViaISBNTask,
)
from ia_scribe.tasks.book import BookTask
from ia_scribe.tasks.composite import (
    MakeReserveAndPrintSlipTask,
    MakeAndPrintSlipTask,
)
from ia_scribe.tasks.print_slip import (
    REJECTED_DO_NOT_WANT_SLIP,
    REJECTED_CAN_NOT_SCAN_SLIP,
    SCANNED_SLIP,
    SCANNED_NO_MARC_SLIP,
)
from ia_scribe.tasks.print_qr_label import PrintQRLabelTask
from ia_scribe.tasks.ia_identifier import MakeIdentifierTask
from ia_scribe.uix_backends.widget_backend import WidgetBackend
from ia_scribe.tasks.ui_handlers.generic import GenericUIHandler
from ia_scribe.tasks.marc_import import MetadataViaMARCTask
from ia_scribe.ia_services.rcs import RCS

class BookMetadataScreenBackend(WidgetBackend):

    EVENT_IDENTIFIER_LOADED = 'on_identifier_loaded'
    EVENT_IDENTIFIER_SAVED = 'on_identifier_saved'
    EVENT_BOOK_STATE = 'on_book_state'
    EVENT_METADATA_SAVED = 'on_metadata_saved'
    EVENT_METADATA_LOADED = 'on_metadata_loaded'
    EVENT_METADATA_ERROR = 'on_metadata_error'
    EVENT_METADATA_DEFERRED = 'on_metadata_deferred'
    EVENT_OFFLINE_ITEM_CREATED = 'on_offline_item_created'
    EVENT_SELECT_IDENTIFIER = 'on_select_identifier'
    EVENT_START_MARC = 'on_start_marc'
    EVENT_NEW_BOOK_CREATED = 'on_new_book_created'
    EVENT_BOOK_REJECTED= 'on_book_rejected'
    EVENT_START_WONDERFETCH = 'on_start_wonderfetch'
    EVENT_END_WONDERFETCH_SUCCESS = 'on_end_wonderfetch_success'
    EVENT_END_WONDERFETCH_FAILURE = 'on_end_wonderfetch_failure'
    EVENT_SLIP_PRINTED = 'on_slip_printed'
    EVENT_RCS_UPDATED = 'on_rcs_updated'

    _book_state = NumericProperty()

    __events__ = (EVENT_IDENTIFIER_LOADED, EVENT_IDENTIFIER_SAVED, EVENT_BOOK_STATE, EVENT_METADATA_LOADED,
                  EVENT_METADATA_ERROR, EVENT_SELECT_IDENTIFIER,
                  EVENT_OFFLINE_ITEM_CREATED, EVENT_NEW_BOOK_CREATED,
                  EVENT_START_MARC, EVENT_METADATA_SAVED, EVENT_METADATA_DEFERRED,
                  EVENT_BOOK_REJECTED, EVENT_START_WONDERFETCH, EVENT_END_WONDERFETCH_SUCCESS, EVENT_SLIP_PRINTED,
                  EVENT_RCS_UPDATED)


    def __init__(self, **kwargs):
        self._identifier = None
        self._metadata = None
        self._new_book = False
        self._config = Scribe3Configuration()
        self.book_obj = None
        self.books_db = kwargs.pop('books_db', Library())
        self.rcs_manager = RCS()
        self.rcs_manager.subscribe(self._rcs_update_handler)
        self.task_scheduler = kwargs.pop('task_scheduler')
        self.books_dir = kwargs.get('books_dir', None) or BOOKS_DIR
        self.book_path = kwargs.get('book_path', None)
        self.config_path = kwargs.get('config_path', None) or CONFIG_DIR
        super(BookMetadataScreenBackend, self).__init__(**kwargs)

    def init(self):
        if not self.is_initialized():
            self._reload_book_state()
            self._load_metadata_from_disk()
            super(BookMetadataScreenBackend, self).init()
            self._load_identifier()

    def reset(self):
        if self.is_initialized():
            self._identifier = None
            self._metadata = None
            self._book_state = 0
            self._new_book = False
            self.book_obj = None
            self.logger = Logger
            super(BookMetadataScreenBackend, self).reset()

    def is_this_a_supercenter(self):
        sc_metadata = get_sc_metadata()
        ret = sc_metadata['scanningcenter'] in scribe_globals.SUPERCENTERS
        return ret

    def get_metadata(self):
        if self._metadata:
            return copy(self._metadata)
        return None

    def get_identifier(self):
        return self._identifier

    def get_book_state(self):
        return self._book_state

    def create_new_cd(self, ):
        self.reset()
        generated_uuid = str(uuid4())
        meta = get_sc_metadata()
        user = meta.get('operator')
        scanningcenter = meta.get('scanningcenter')
        self.book_obj = self.books_db.new_cd(generated_uuid,
                                               operator=user,
                                               scanningcenter=scanningcenter)
        self.book_path = self.book_obj.path

    def create_new_book(self):
        self.reset()
        generated_uuid = str(uuid4())
        meta = get_sc_metadata()
        user = meta.get('operator')
        scanningcenter = meta.get('scanningcenter')
        self.book_obj = self.books_db.new_book(generated_uuid,
                                               operator=user,
                                               scanningcenter=scanningcenter)
        self.book_path = self.book_obj.path

    def _rcs_update_handler(self, *args, **kwargs):
        self.dispatch(self.EVENT_RCS_UPDATED)

    def create_form_collection_sets(self):
        ret = self.rcs_manager.get_current_collection_sets()
        return ret

    def create_collections(self, collection_set):
        ret = self.rcs_manager.get_collections_by_name(collection_set)
        return ret

    def add_collection_set(self, widget, rcs_data):
        self.rcs_manager.add(rcs_data)

    def save_metadata(self):
        path = self.book_path
        new_book = not exists(path)
        if self._metadata and path:
            ensure_book_directory(path)
            if 'user_identifier' in self._metadata:
                self._set_identifier(self._metadata['user_identifier'])
                del(self._metadata['user_identifier'])
            if 'ppi' in self._metadata:
                self.set_ppi(self._metadata['ppi'])
                del(self._metadata['ppi'])
            if self.book_obj.is_preloaded():
                if 'collection' in self._metadata:
                    del(self._metadata['collection'])
                if 'collection_set' in self._metadata:
                    del (self._metadata['collection_set'])
            set_metadata(self._metadata, path)
            self.dispatch(self.EVENT_METADATA_SAVED)

    def set_ppi(self, ppi):
        self.book_obj.scandata.set_bookdata('ppi', ppi)
        self.book_obj.scandata.save()
        self._config.set('camera_ppi', ppi)

    def create_form_metadata(self, skip_keys=None):
        out = []
        new_book = not (self.book_path
                        and exists(join(self.book_path, 'metadata.xml')))
        skip_keys = skip_keys or set()
        metadata = self._metadata or {}
        metadata_keys = set(MD_NEW_BOOK_KEYS if new_book else MD_REQUIRED_KEYS)
        if metadata:
            metadata_keys.update(metadata.keys())
        metadata_keys = metadata_keys.difference(skip_keys)
        for key in self._sort_metadata_keys(metadata_keys):
            temp = {'key': key, 'new_book': new_book}
            value = metadata.get(key, '')
            if key in MD_READONLY_KEYS:
                temp['readonly'] = True
            if key in MD_REQUIRED_KEYS:
                temp['required'] = True
            if isinstance(value, list):
                for index, item in enumerate(value):
                    new_temp = deepcopy(temp)
                    if index > 0 and new_temp.get('required', False):
                        new_temp['required'] = False
                    new_temp['value'] = item
                    out.append(new_temp)
            else:
                temp['value'] = value
                out.append(temp)
        return out

    def _sort_metadata_keys(self, keys):
        keys = set(keys)
        it = iter(MD_ORDERED_KEYS)
        while keys:
            ordered_key = next(it, None)
            if ordered_key is None:
                break
            if ordered_key in keys:
                yield ordered_key
                keys.remove(ordered_key)
        for key in keys:
            yield key

    def set_metadata_from_form(self, form_metadata):
        key_getter = itemgetter('key')
        value_getter = itemgetter('value')
        md = self._metadata.copy() if self._metadata else {}
        for item in filter(lambda x: x.get('deleted', False), form_metadata):
            md.pop(item['key'], None)
        not_deleted_md = filter(lambda x: not x.get('deleted', False),
                                form_metadata)
        sorted_md = sorted(not_deleted_md, key=key_getter)
        for key, item_values in groupby(sorted_md, key_getter):
            values = list(map(value_getter, item_values))
            if len(values) == 1:
                values = values[0]
            md[key] = values
        self._set_metadata(md)

    def get_metadata_item(self, key):
        ret = self._metadata.get(key, None) if self._metadata else None
        return ret

    def set_metadata_item(self, key, value):
        if not self._metadata:
            self._metadata = {}
        if isinstance(value, list):
            # Save a copy of the list
            value = list(value)
        if key not in self._metadata:
            self._metadata[key] = value
            self.dispatch(self.EVENT_METADATA_LOADED)
        elif self._metadata[key] != value:
            self._metadata[key] = value
            self.dispatch(self.EVENT_METADATA_LOADED)

    def set_metadata(self, metadata):
        self._set_metadata(metadata)
        self._load_identifier()

    def update_metadata(self, metadata):
        _metadata = self._metadata
        for key, value in metadata.items():
            if isinstance(value, list):
                value = list(value)
            _metadata[key] = value
        self.dispatch(self.EVENT_METADATA_LOADED)

    def _reload_book_state(self):
        book_path = self.book_path
        if not book_path:
            self._book_state = 0
            return
        state = 0
        if exists(join(book_path, 'identifier.txt')):
            state |= ST_HAS_IDENTIFIER
        if exists(join(book_path, 'delete_queued')):
            state |= ST_QUEUED_FOR_DELETE
        if exists(join(book_path, 'preloaded')):
            state |= ST_PRELOADED
        if exists(join(book_path, 'downloaded')):
            state |= ST_DOWNLOADED
        if exists(join(book_path, 'marc.xml')):
            state |= ST_HAS_MARC_XML
        if exists(join(book_path, 'marc.bin')):
            state |= ST_HAS_MARC_BIN
        if exists(join(book_path, 'metasource.xml')):
            state |= ST_HAS_METASOURCE
        self._book_state = state
        uuid = basename(self.book_path)
        self.book_obj = self.books_db.get_item(uuid)
        self.book_obj.logger.info('BDMS: Loaded')
        self.logger = self.book_obj.logger

    def _load_metadata_from_disk(self):
        if self.book_path and exists(self.book_path):
            self._set_metadata(get_metadata(self.book_path))
        else:
            self._set_metadata(None)

    def _set_metadata(self, metadata):
        if metadata:
            self._ensure_valid_metadata(metadata)
            self._update_legacy_keys_in_metadata(metadata)
        else:
            metadata = {}
            self._ensure_valid_metadata(metadata)
        self._metadata = metadata
        self.dispatch(self.EVENT_METADATA_LOADED)

    def _has_minimum_acceptable_metadata(self):
        return self.book_obj.has_minimal_metadata()

    def _ensure_valid_metadata(self, metadata):
        for key in metadata:
            if key in MD_KEYS_WITH_SINGLE_VALUE \
                    and isinstance(metadata[key], list) \
                    and len(metadata[key]) > 1:
                first_value = metadata[key][0]
                self.logger.warn('BookMetadataScreenBackend: Found more than'
                                 'one value of "{0}" in book metadata. '
                                 'Adjusting to use first value of {1}, '
                                 'so md[{0}] => {2}'
                                 .format(key, metadata[key], first_value))
                metadata[key] = first_value
        config = self._config
        ppi = metadata.get('ppi', None)
        if isinstance(ppi, list):
            ppi = ppi[0]
        if ppi is None or int(float(ppi)) < 1:
            ppi = config.get('camera_ppi', None)
            if ppi is None or int(float(ppi)) < 1:
                ppi = DEFAULT_PPI
            metadata['ppi'] = int(float(ppi))
        else:
            metadata['ppi'] = int(float(ppi))
        sc_metadata = get_sc_metadata()
        operator = self.book_obj.operator \
            if self.book_obj.operator is not None else sc_metadata.get('operator')
        scanningcenter = self.book_obj.scanningcenter \
            if self.book_obj.scanningcenter is not None else sc_metadata.get('scanningcenter')
        metadata.setdefault('operator', operator)
        metadata.setdefault('scanningcenter', scanningcenter)

        if 'language' not in metadata:
            if config.is_true('prefill_language'):
                language = sc_metadata.get('language', None)
                if language:
                    metadata['language'] = language

    def _update_legacy_keys_in_metadata(self, metadata):
        author = metadata.pop('author', None)
        if author is not None and metadata.get('creator', None) is None:
            metadata['creator'] = author

    def flag_book_for_delete(self):
        task = self._create_task(BookTask,
                                 book=self.book_obj,
                                 command='do_move_to_trash')
        self.task_scheduler.schedule(task)
        self._book_state |= ST_QUEUED_FOR_DELETE
        self.logger.debug('BMDS: Queued {} for delete'.format(self.book_obj))

    def load_metadata_via_identifier(self, identifier):
        self.logger.info('BMDS: Load metadata using identifier: {}'
                         .format(identifier))

        task = self._create_task(MetadataViaIdentifierTask,
                                 book = self.book_obj,
                                 identifier=identifier)
        task.fbind('on_end', self._on_load_metadata_via_identifier_end)
        self.task_scheduler.schedule(task)

    def _on_load_metadata_via_identifier_end(self, task, *args):
        task.funbind('on_end', self._on_load_metadata_via_identifier_end)
        if task.error:
            if task.is_metadata_load_failed():
                self.dispatch(self.EVENT_METADATA_ERROR, task.identifier)
                return
            elif task.should_delete_book():
                self.dispatch(self.EVENT_ERROR, task.error.message if hasattr(task.error, 'message') else task.error)
                self.flag_book_for_delete()
                return
            self.reinit()
            self.dispatch(self.EVENT_ERROR, task.error.message if hasattr(task.error, 'message') else task.error)
        else:
            self.reinit()
            #self.dispatch(self.EVENT_END_WONDERFETCH_SUCCESS)

    def _load_identifier(self):
        # POLICY CHANGE: Identifier.txt takes priority
        if self.book_path:
            path = join(self.book_path, 'identifier.txt')
            if exists(path):
                identifier = open(path).read().strip()
                self._set_identifier(identifier)
                return

        if self._metadata:
            identifier = self._metadata.get('identifier', None)
            if identifier is not None:
                self._set_identifier(identifier)
                return

        self._set_identifier(None)

    def _set_identifier(self, identifier):
        if self._identifier != identifier:
            self._identifier = identifier
            if identifier:
                self._book_state |= ST_HAS_IDENTIFIER
            else:
                self._book_state &= ~ST_HAS_IDENTIFIER
            self._save_identifier(identifier)
        self.dispatch(self.EVENT_IDENTIFIER_LOADED, identifier)

    def _save_identifier(self, identifier):
        ensure_book_directory(self.book_path)
        path = join(self.book_path, 'identifier.txt')
        if not identifier and exists(path):
            os.remove(path)
            self.logger.info('BMDS: Removed identifier from: {}'.format(path))
        else:
            with open(path, 'w') as fd:
                fd.write(identifier)
            self.dispatch(self.EVENT_IDENTIFIER_SAVED, identifier)
            self.logger.info('BMDS: Saved identifier at: {}'.format(path))

    def can_reprint_slip(self):
        return self.book_obj.has_slip() if self.book_obj else False

    def load_metadata_via_isbn(self, isbn, volume=''):
        self.logger.info('BMDS: Load metadata using ISBN: {}, volume: {}'.format(isbn, volume))
        task = self._create_task(MetadataViaISBNTask, isbn=isbn)
        task.volume = volume
        task.fbind('on_end', self._on_load_metadata_via_isbn_end)
        self.task_scheduler.schedule(task)

    def _on_load_metadata_via_isbn_end(self, task):
        task.funbind('on_end', self._on_load_metadata_via_isbn_end)
        if task.error:
            self.dispatch(self.EVENT_ERROR, task.error.message)
        else:
            if task.should_select_identifier():
                self.dispatch(self.EVENT_SELECT_IDENTIFIER, task.archive_ids)

    def wonderfetch_search(self, method, identifier, volume='', catalog = None, old_pallet = None):
        self.logger.info('BMDS: Dispatch event to start Wonderfetch search')
        self.dispatch(self.EVENT_START_WONDERFETCH, method, identifier, volume, catalog)

    def load_metadata_via_openlibrary(self, payload, extra, search_id, volume='',):
        self.logger.info('BMDS: Load metadata via OpenLibrary using '
                         'uuid={}, volume={}'.format( search_id, volume))
        task = self._create_task(MetadataViaOpenlibraryTask,
                                 book_path=self.book_path,
                                 book=self.book_obj,
                                 extra=extra,
                                 volume=volume,
                                 search_id=search_id,
                                 payload=payload)
        task.fbind('on_end', self._on_load_metadata_via_external_provider)
        self.task_scheduler.schedule(task)

    def _on_load_metadata_via_external_provider(self, task):
        task.funbind('on_end', self._on_load_metadata_via_external_provider)
        if task.error:
            self.dispatch(self.EVENT_ERROR,
                          task.error.message if hasattr(task.error, 'message')
                                             else task.error)
        self.reinit()

    def extract_metadata_from_marc_search(self, query, data):
        task_handler = GenericUIHandler(
            task_type=MetadataViaMARCTask,
            book=self.book_obj,
            query=query,
            data=data,
            )
        task_handler.task.fbind('on_end', self._on_load_metadata_via_external_provider)
        self.task_scheduler.schedule(task_handler.task)

    def reject_book(self, data):
        self.logger.info('BMDS: Print rejection slip')
        metadata = {}
        metadata.update(data)
        sc_metadata = get_sc_metadata()
        metadata['scanner'] = sc_metadata['scanner']
        metadata['datetime'] = datetime.datetime.now()
        metadata['timestamp'] = time.time()
        task = self._create_task(MakeAndPrintSlipTask,
                                 book = self.book_obj,
                                 type=REJECTED_CAN_NOT_SCAN_SLIP,
                                 slip_metadata = metadata,
                                 transition='do_reject')
        task.fbind('on_end', self._on_reject_book_end)
        self.task_scheduler.schedule(task)

    def _on_reject_book_end(self, task):
        task.funbind('on_end', self._on_reject_book_end)
        if task.error:
            self.dispatch(self.EVENT_ERROR, 'Failed to print slip\nError was: {}'.format(task.error))
        else:
            self.logger.info('Dispatching EVENT_BOOK_REJECTED')
            self.dispatch(self.EVENT_BOOK_REJECTED, task)
            '''
            if exists(self.book_path):
                self.logger.info('Book was rejected, now flagging for deletion')
                self.flag_book_for_delete()
            '''

    def cannot_scan_book(self, catalog, selector, response):
        self.logger.info('BMDS: Print DO NOT WANT rejection slip')
        metadata = {}
        sc_metadata = get_sc_metadata()
        metadata['scanner'] = sc_metadata['scanner']
        metadata['datetime'] = datetime.datetime.now()
        metadata['reason'] = 'Duplicate'
        metadata['comment'] = response.get('keep_dupe_message')
        metadata['keep_dupe_status'] = response.get('keep_dupe_status')
        metadata['keep_dupe_status_code'] = response.get('keep_dupe_status_code')
        metadata['dwwi_response'] = response
        metadata['catalog'] = catalog
        metadata['selector'] = selector
        metadata['timestamp'] = time.time()
        task = self._create_task(MakeAndPrintSlipTask,
                                 book=self.book_obj,
                                 type=REJECTED_DO_NOT_WANT_SLIP,
                                 slip_metadata=metadata,
                                 transition='do_move_to_trash')
        task.fbind('on_end', self._on_reject_book_end)
        self.task_scheduler.schedule(task)

    def marc_search(self, identifier):
        self.logger.info('BMDS: Dispatch event to start MARC search')
        self.dispatch(self.EVENT_START_MARC, identifier)

    def print_qr_label(self, identifier):
        self.logger.info('BMDS: Print qr label')
        task = self._create_task(PrintQRLabelTask,
                                 book_path=self.book_path,
                                 text=identifier,
                                 identifier=self._identifier,
                                 metadata=self.get_metadata())
        task.fbind('on_end', self._on_print_qr_label_end)
        self.task_scheduler.schedule(task)

    def _on_print_qr_label_end(self, task):
        task.funbind('on_end', self._on_print_qr_label_end)
        if task.error:
            self.dispatch(self.EVENT_ERROR, 'Failed to print QR label')
        else:
            # Update identifier in case that task created new one
            self._set_identifier(task.identifier)

    def generate_and_print_slip(self, identifier):
        self.logger.info('BMDS: Generate slip')
        metadata = {}
        slip_type = SCANNED_SLIP if ('title' in self.book_obj.metadata
                                     and 'creator' in self.book_obj.metadata) \
                else SCANNED_NO_MARC_SLIP
        sc_metadata = get_sc_metadata()
        metadata['scanner'] = sc_metadata['scanner']
        metadata['identifier'] = identifier
        metadata['datetime'] = datetime.datetime.now()
        metadata['timestamp'] = time.time()
        task = self._create_task(MakeAndPrintSlipTask,
                                 type = slip_type,
                                 book=self.book_obj,
                                 slip_metadata = metadata)
        task.fbind('on_end', self._on_generate_and_print_slip_end)
        self.task_scheduler.schedule(task)

    def _on_generate_and_print_slip_end(self, task):
        task.funbind('on_end', self._on_generate_and_print_slip_end)
        self.logger.info('BMDS: Generate slip end')
        if task.error:
            self.dispatch(self.EVENT_ERROR, 'Failed to generate slip\nError was: {}'.format(task.error))
        else:
            self.logger.info('BMDS: Generate slip success')
            self.dispatch(self.EVENT_SLIP_PRINTED)

    def generate_reserve_print_slip(self, identifier, next_action=None):
        self.logger.info('BMDS: Reserving identifier on IA and printing slip')
        metadata = {}
        slip_type = SCANNED_SLIP if ('title' in self.book_obj.metadata
                                     and 'creator' in self.book_obj.metadata) \
            else SCANNED_NO_MARC_SLIP
        sc_metadata = get_sc_metadata()
        metadata['scanner'] = sc_metadata['scanner']
        metadata['identifier'] = identifier
        metadata['datetime'] = datetime.datetime.now()
        metadata['timestamp'] = time.time()
        #assert self.book_obj.identifier == identifier, \
        #    'The identifier in the text box and the one saved on disk differ.'
        task = self._create_task(MakeReserveAndPrintSlipTask,
                                 book=self.book_obj,
                                 type=slip_type,
                                 slip_metadata=metadata,
                                 transition=next_action)
        task.fbind('on_progress', task._on_make_reserve_print_slip_progress)
        task.fbind('on_end', self._on_generate_reserve_print_slip_end)
        self.task_scheduler.schedule(task)

    def _on_generate_reserve_print_slip_end(self, task):
        task.funbind('on_end', self._on_generate_reserve_print_slip_end)
        if task.error:
            self.dispatch(self.EVENT_ERROR, 'Failed to reserve item or print slip\nError was: {}'.format(task.error))
        else:
            self.logger.info('BMDS: Item successfully registered on IA')
            self.dispatch(self.EVENT_SLIP_PRINTED)

    def make_identifier(self,  volume = ''):
        self.logger.info('BMDS: Make identifier pressed')
        task = self._create_task(MakeIdentifierTask,
                                 book=self.book_obj)
        task.fbind('on_end', self._on_make_identifier_end)
        self.task_scheduler.schedule(task)

    def _on_make_identifier_end(self, task):
        task.funbind('on_end', self._on_make_identifier_end)
        if task.error:
            self.dispatch(self.EVENT_ERROR, 'Failed to create identifier')
        else:
            self.logger.info('BMDS: Successfuly made an identifier: {}'.format(task.identifier))
            self.reinit()

    def create_offline_item(self, identifier):
        self._set_identifier(identifier)
        self._save_preloaded_file()
        self.dispatch(self.EVENT_OFFLINE_ITEM_CREATED)

    def _save_preloaded_file(self):
        ensure_book_directory(self.book_path)
        path = join(self.book_path, 'preloaded')
        open(path, 'w').close()
        self._book_state |= ST_PRELOADED
        self.logger.info('BMDS: Created preloaded file: {}'.format(path))

    def on__book_state(self, backend, state):
        self.dispatch(self.EVENT_BOOK_STATE, state)

    def on_new_book_created(self, book):
        self.logger.info('BMDS: New book created:{}{}'
                         .format(os.linesep, pformat(book)))

    def on_identifier_loaded(self, identifier):
        if not identifier:
            return
        if not self.books_db:
            self.logger.warn('on_identifier could not find a workable library list')
            return
        if not self.book_obj:
            uuid = basename(self.book_path)
            book_record = self.books_db.get_item(uuid)
        else:
            book_record = self.book_obj
        task = self._create_task(BookTask,
                                 book=book_record,
                                 command='update',
                                 args=[{'identifier': identifier},])
        self.task_scheduler.schedule(task)


    def on_identifier_saved(self, identifier):
        if not self.books_db:
            self.logger.warn('on_identifier_saved could not find a workable library list')
            return
        if not self.book_obj:
            uuid = basename(self.book_path)
            book_record = self.books_db.get_item(uuid)
        else:
            book_record = self.book_obj
        if book_record:
            if book_record.not_has_identifier():
                if book_record.can('do_create_identifier'):
                    task = self._create_task(BookTask,
                                             book=book_record,
                                             command='do_create_identifier',)
                    self.task_scheduler.schedule(task)
                task = self._create_task(BookTask,
                                         book=book_record,
                                         command='reload_metadata', )
                self.task_scheduler.schedule(task)

    def on_book_state(self, state):
        pass

    def on_metadata_saved(self):
        if not self.books_db:
            self.logger.warn('on_metadata_saved could not find a workable library list')
            return
        uuid = basename(self.book_path)
        book_record = self.books_db.get_item(uuid)
        if book_record:
            book_record.reload_metadata()
            if book_record.can('do_create_metadata'):
                book_record.do_create_metadata()

    def on_metadata_loaded(self):
        pass

    def on_metadata_error(self, identifier):
        pass

    def on_offline_item_created(self):
        pass

    def on_select_identifier(self, identifiers):
        pass

    def on_start_marc(self, identifier):
        pass

    def on_start_wonderfetch(self, method, identifier, volume = '', catalog=None):
        pass

    def on_end_wonderfetch_success(self):
        pass

    def on_end_wonderfetch_failure(self, error, wid, method, catalog):
        self._metadata['scribe3_search_id'] = wid
        self._metadata['scribe3_search_method'] = method
        self._metadata['scribe3_search_catalog'] = catalog
        self.save_metadata()
        if self.book_obj.can('do_defer_metadata'):
            self.book_obj.do_defer_metadata()
            self.dispatch(self.EVENT_METADATA_DEFERRED)

    def on_book_rejected(self, task):
        try:
            slip_metadata = task._slip_metadata
            cleaned_md = {k: '{}'.format(v).encode('utf-8').decode('utf-8')
                          for k, v in self.book_obj.metadata.items()}
            payload = {'reason': slip_metadata['reason'],
                       'error': slip_metadata['error'] if 'error' in slip_metadata else '',
                       'comment': slip_metadata['comment'] if 'comment' in slip_metadata else '',
                       'book_metadata': cleaned_md,
                       }

            push_event('tts-book-dwwi-reject', payload)
            self.logger.info('CaptureScreen: Pushed event tts-book-reject to '
                        'iabdash with payload: {}'.format(payload))
        except Exception as e:
            self.logger.exception('CaptureScreen: Failed to push tts-book-reject '
                             'event because: {}'.format(e))

    def on_metadata_deferred(self, *args, **kwargs):
        pass

    def on_slip_printed(self, *args, **kwargs):
        pass

    def on_rcs_updated(self, *args, **kwargs):
        pass
