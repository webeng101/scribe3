import os
import threading
from os.path import join, exists
from enum import Enum
import logging, glob, time
import json
from datetime import datetime

from fysom import *
from ia_scribe.book.states import media_state_machine
from ia_scribe.book.smau import (available_next_actions,
                                 available_next_states,
                                 path_to_deletion,
                                 path_to_state)
from ia_scribe.book.upload_status import status_human_readable
from ia_scribe.utils import all_files_under, ensure_book_directory
from ia_scribe.abstract import thread_safe, Observable
from ia_scribe.tasks.book_tasks.identifier import new_get_identifier
from ia_scribe.book.upload_status import UploadStatus

from ia_scribe.book.metadata import get_metadata, set_metadata
from ia_scribe.book.scandata import ScanData

from ia_scribe import scribe_globals

IDENTIFIER_NAME = 'identifier.txt'
LOG_FILENAME = 'scanning.log'
DEFAULT_STATE = 'uuid_assigned'


class Scribe3Item(FysomGlobalMixin, Observable):
    state_machine = media_state_machine
    error = None
    observers = set([])

    def __init__(self, init_dict, callback=None, delete_callback=None):
        print("[Item::init()] Creating item object from ->", init_dict)
        self.GSM = FysomGlobal(
            cfg=self.state_machine,
            state_field='status',
        )

        self.constructor_args = init_dict
        self.uuid = init_dict['uuid']
        self.path = init_dict['path'] if 'path' in init_dict else self.build_path()
        self.exists = os.path.exists(self.path)

        self.TYPE_FILE = os.path.expanduser(os.path.join(self.path, 'type'))
        self.STATUS_FILE = os.path.expanduser(os.path.join(self.path, 'status'))
        self.STATUS_HISTORY_FILE = os.path.expanduser(os.path.join(self.path, 'status_history'))
        if not self.exists:
            self.ensure_path()

        self._set_type()

        self.logger = self.get_logger()
        self.status = self._resolve_status(init_dict)

        self.MINIMAL_METADATA_MANIFEST = ['title', 'creator', 'operator', 'scanningcenter', 'scanner']
        self.metadata = get_metadata(self.path)
        if len(self.metadata) == 0:
            self.create_initial_metaxml()

        self.identifier = new_get_identifier(self)
        self.title = init_dict['title'] if 'title' in init_dict else self.metadata[
            'title'] if 'title' in self.metadata else None
        self.creator = init_dict['creator'] if 'creator' in init_dict else self.metadata[
            'creator'] if 'creator' in self.metadata else None

        self.date_last_updated = init_dict['date'] if 'date' in init_dict \
            else self.load_last_modified_from_disk(including_move_along=True)
        self.date_last_modified = init_dict['date_last_modified'] if 'date_last_modified' in init_dict \
            else self.load_last_modified_from_disk()
        self.date_created = init_dict['date_created'] if 'date_created' in init_dict \
            else self.load_date_created_from_disk()
        self.operator = init_dict['operator'] if 'operator' in init_dict else self.metadata[
            'operator'] if 'operator' in self.metadata else None
        self.scanner = init_dict['scanner'] if 'scanner' in init_dict else self.metadata[
            'scanner'] if 'scanner' in self.metadata else None
        self.scanningcenter = init_dict['scanningcenter'] if 'scanningcenter' in init_dict else self.metadata[
            'scanningcenter'] if 'scanningcenter' in self.metadata else None

        self.error = init_dict['error'] if 'error' in init_dict else None
        self.worker_log = ''
        self.msg = ''

        self.last_activity = ''

        self.force_upload = False
        self.force_delete = False

        self.delete_callback = delete_callback
        self.natural_callback = callback

        callbacks = self.build_callbacks()
        self.GSM._callbacks = callbacks

        self.worker_lock = threading.RLock()

        super(Scribe3Item, self).__init__()

    def __getitem__(self, input):
        me = self.as_dict()
        ret = me[input]
        return ret

    def __repr__(self):
        ret = '<{} is {} '.format(self.uuid, self.status)
        if self.has_identifier():
            ret = ret + '| {}'.format(self.identifier)
        ret = ret + '>'
        return ret

    def _set_type(self):
        if not os.path.exists(self.TYPE_FILE):
            with open(self.TYPE_FILE, 'w+') as f:
                f.write(self.get_type())

    def get_type(self):
        return self.__class__.__name__

    def set_lock(self, blocking = False):
        res = self.worker_lock.acquire(blocking)
        #self.logger.debug('Lock acquire called: {}, {}'.format(res, self.worker_lock))
        return res

    def release_lock(self):
        self.worker_lock.release()

    def is_locked(self):
        return 'count=0' not in self.worker_lock.__repr__()

    def get(self, attr, *args, **kwargs):
        if hasattr(self, attr):
            return getattr(self, attr)
        else:
            return None

    def notify(self, event, topic='events'):
        for observer in self.observers:
            observer(event, self, topic)
        self.natural_callback(event, self, topic)
        if event not in [ 'state_change' , 'message-updated', ]:
            self.last_activity = event

    def ensure_path(self):
        ensure_book_directory(self.path)
        self.exists = True

    def initialze_metaxml(self):
        '''
        The typical MD write path goes through the MD panel,
        which is responsible for performing all the various checks on values prior to dumping to xml.
        This is deliberate, so that the MD panel is the effective chokepoint for all MD edits.
        This object family mostly operates as a lightweigh read-only wrapper. Whenever the metadata is updated
        a call to reload_metadata() is issued. However, in some cases (like in extensions) we may want to offer
        the ability to create a metadata.xml without jumping through more hoops. This is what this function is for.
        '''
        current_md = get_metadata(self.path)
        if current_md:
            raise Exception('Metadata has already been initialized')
        md = {}
        for key in self.MINIMAL_METADATA_MANIFEST:
            md[key] = getattr(self, key)
        set_metadata(md, self.path)
        self.reload_metadata()

    def create_initial_metaxml(self):
        '''
        Create initial metadata.xml file when book is created newly and not exist metadata.xml file.
            <collection>booksgrouptest</collection>
            <contributor>Internet Archive</contributor>
            <sponsor>Internet Archive</sponsor>
        
        '''
        trial_md = {'collection': 'booksgrouptest', 'contributor':'Internet Archive', 'sponsor':'Internet Archive'}
        set_metadata(trial_md, self.path)

    def reload_metadata(self):
        self.metadata = get_metadata(self.path)
        self.title = self.metadata['title'] if 'title' in self.metadata else None
        self.creator = self.metadata['creator'] if 'creator' in self.metadata else None
        self.operator = self.metadata['operator'] if 'operator' in self.metadata else None
        self.scanner = self.metadata['scanner'] if 'scanner' in self.metadata else None
        self.scanningcenter = self.metadata['scanningcenter'] if 'scanningcenter' in self.metadata else None
        self.exists = os.path.exists(self.path)
        self.identifier = new_get_identifier(self)
        self.date_last_updated = self.load_last_modified_from_disk(including_move_along=True)
        self.date_last_modified = self.load_last_modified_from_disk()
        self.date_created = self.load_date_created_from_disk()
        if self.notify:
            self.notify('reloaded_metadata')

    def reload_scandata(self):
        self.scandata = ScanData(self.path)
        self.date_last_updated = self.load_last_modified_from_disk(including_move_along=True)
        self.date_last_modified = self.load_last_modified_from_disk()
        self.date_created = self.load_date_created_from_disk()
        if self.notify:
            self.notify('reloaded_scandata')

    def name_human_readable(self):
        return self.identifier if self.has_identifier() else self.uuid

    def update_message(self, message):
        self.msg = message
        self.notify('message-updated')

    def get_status(self, human_readable=False):
        ret = self.status
        if human_readable:
            ret = status_human_readable[self.status]
        return ret

    def get_status_history(self, raw=False):
        def parse_history_line(line):
            raw_timestamp, raw_status = line.split(',')
            timestamp = datetime.fromtimestamp(
                                    float(raw_timestamp))\
                                    .strftime('%a %Y %b %d | %H:%M:%S')
            status = raw_status.strip('\n')
            ret = '{} -> {}'.format(timestamp, self.humanify([status])[0])
            return ret

        ret = []
        try:
            with open(self.STATUS_HISTORY_FILE, 'r') as f:
                for line in f.readlines():
                    entry = line if raw else parse_history_line(line)
                    ret.append(entry)
        except Exception as e:
            self.logger.exception(e)
        return ret

    def _resolve_status(self, book_dict):
        # this function contains the logic to honor
        # statuses passed in the constructor
        # If a file is present and the statues differ,
        # we throw an exception
        # if it doesn't exist (e.f. download_incomplete),
        # we honor that. Otherwise we assume DEFAULT_STATUS
        if 'status' in book_dict:
            disk_state = self.load_status_from_disk()
            if disk_state:
                if disk_state != book_dict['status']:
                    msg = 'The constructor is asking to build a Book in {} \
                          status, but the on-disk record says it is in {} \
                          status. Do not know what to do. Giving up.'
                    raise Exception(msg)
            else:
                with open(self.STATUS_FILE, 'w+') as f:
                    f.write(book_dict['status'])
                with open(self.STATUS_HISTORY_FILE, 'a+') as f:
                    line = '{},{}\n'.format(time.time(), book_dict['status'])
                    f.write(line)
            return book_dict['status']
        else:
            return self._upget_status_file()

    def _upget_status_file(self):
        #upget like a reverse upsert. Get value
        # from disk if present, otherwise create
        # file and assume the default
        disk_state = self.load_status_from_disk()
        if disk_state:
            return disk_state
        else:
            with open(self.STATUS_FILE, 'w+') as f:
                f.write(DEFAULT_STATE)
            with open(self.STATUS_HISTORY_FILE, 'a+') as f:
                line = '{},{}\n'.format(time.time(), DEFAULT_STATE)
                f.write(line)
            self.logger.info('Created item with status: {}'.format(DEFAULT_STATE))
            return DEFAULT_STATE

    def load_status_from_disk(self):
        state = None
        if os.path.exists(self.STATUS_FILE):
            with open(self.STATUS_FILE, 'r+') as f:
                state = f.read().strip('\n')
        if state is not None and len(state) == 0:
            state = None
        return state

    def load_last_modified_from_disk(self, including_move_along=False):
        if self.exists:
            book_files = list(all_files_under(self.path))
            if including_move_along:
                filtered_book_files = book_files
            else:
                filtered_book_files = [x for x in book_files if not x.endswith(LOG_FILENAME)]
            initial_file = max(filtered_book_files, key=os.path.getmtime)
            ret = os.path.getmtime(initial_file)
            return ret
        else:
            return time.time()

    def load_date_created_from_disk(self):
        if self.exists:
            book_files = list(all_files_under(self.path))
            filtered_book_files = [x for x in book_files if not x.endswith(LOG_FILENAME)]
            latest_file = min(filtered_book_files, key=os.path.getctime)
            ret = os.path.getctime(latest_file)
            return ret
        else:
            return time.time()

    @thread_safe
    def update(self, delta):
        did_update = False
        for key, value in delta.items():
            if hasattr(self, key):
                if getattr(self, key) != value:
                    setattr(self, key, value)
                    did_update = True
        if did_update and self.notify:
            modtime = time.time()
            self.date_last_updated = modtime
            self.date_last_modified = modtime
            self.notify('book_update')

    def as_dict(self):
        ret = {
            'type': self.get_type(),
            'identifier': self.identifier,
            'uuid': self.uuid,
            'path': self.path,
            'status': self.get_numeric_status(),
            'status_human_readable': status_human_readable.get(self.status),
            'title': self.title,
            'creator': self.creator,
            'date': self.date_last_updated,
            'date_last_modified': self.date_last_modified,
            'date_created':self.date_created,
            'operator': self.operator,
            'scanner': self.scanner,
            'error': self.error,
            'worker_log': self.worker_log,
            'msg': self.msg,
        }
        return ret

    def get_logger(self):
        log = logging.getLogger('Item_{:7.7}'.format(self.uuid))
        log.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        if log.handlers:
            log.handlers = []
        formatter = logging.Formatter(scribe_globals.LOGGING_FORMAT)
        handler.setFormatter(formatter)
        log.addHandler(handler)

        try:
            # LOG_FILENAME = '{}.log'.format(datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
            log_file_location = os.path.expanduser(os.path.join(self.path, LOG_FILENAME))
            file_handler = logging.FileHandler(log_file_location)
            file_handler.setFormatter(formatter)
            log.addHandler(file_handler)
        except Exception as e:
                log.error('Could not init file logger at {} because {}'.format(self.path, e))
        log.propagate = 0
        return log

    def build_path(self):
        ret = os.path.expanduser(os.path.join(scribe_globals.BOOKS_DIR, self.uuid))
        return ret

    def has_identifier(self, e=None):
        if hasattr(self, 'identifier'):
            return self.identifier not in ['', None]
        else:
            return False

    def not_has_identifier(self, e=None):
        return not self.has_identifier()

    def set_identifier(self, identifier):
        path = join(self.path, IDENTIFIER_NAME)
        if not identifier and exists(path):
            os.remove(path)
            self.logger.info('Removed identifier from: {}'.format(path))
        else:
            with open(path, 'w') as fd:
                fd.write(identifier)
            self.logger.info('Written {} to {}'.format(identifier,path))
        self.identifier = identifier
        self.notify('identifier-changed')

    def get_available_next_actions(self):
        return available_next_actions(self.status)

    def get_available_next_states(self, human_readable=False):
        available_states = available_next_states(self.status)
        if self.status in available_states:
            available_states.remove(self.status)
        if human_readable:
            available_states = self.humanify(available_states)
        return available_states

    def get_path_to_trash(self, human_readable=False):
        return_value = path_to_deletion(self.status)
        if human_readable:
            return_value = self.humanify(return_value)
        return return_value

    def get_path_to_state(self, state, human_readable=False):
        return_value = path_to_state(self.status, state)
        if human_readable:
            return_value = self.humanify(return_value)
        return return_value

    def raise_exception(self, e, message=None):
        self.error = e.message if hasattr(e, 'message') else str(e)
        if message:
            self.error = '{} : {}'.format(message, self.error)
        self.logger.exception(str(e))
        self.notify(e, 'errors')

    def set_log(self, log):
        self.worker_log = log

    def get_log(self):
        return self.worker_log

    def get_full_log(self):
        ret = ''
        log_file_location = os.path.expanduser(os.path.join(self.path, LOG_FILENAME))
        with open(log_file_location, 'r') as f:
            ret = f.read()
        return ret

    @thread_safe
    def _on_change_state(self, e):
        # do not use 'self' here because the self object is wrapped by fysom
        book = e.obj
        book.error = None
        msg = 'State change: {} -> {}'.format(e.src, e.dst, )
        book.last_activity = msg
        book.logger.info(msg)
        book.save_status_to_disk()
        book.date = time.time()

        if book.notify:
            book.notify('state_change')

    @thread_safe
    def save_status_to_disk(self):
        with open(self.STATUS_FILE, 'w+') as f:
            if self.status:
                f.write(self.status)
        with open(self.STATUS_HISTORY_FILE, 'a+') as f:
            if self.status:
                line = '{},{}\n'.format(time.time(), self.status)
                f.write(line)

    def build_callbacks(self):
        ret = {
            'onchangestate': self._on_change_state,
        }
        return ret

    def get_available_methods(self):
        method_list = [func for func in dir(self) if callable(getattr(self, func)) and not func.startswith("_")]
        gsm_method_list = [func for func in dir(self.GSM) if callable(getattr(self.GSM, func)) and not func.startswith("_")]
        return {'natural': method_list,
                'state_machine': gsm_method_list}

    # this is just here for compatibility reasons, it'll go away
    def unsub(self, observer):
        return self.unsubscribe(observer)

    def humanify(self, statuses_list):
        return [status_human_readable[x] for x in statuses_list]

    def get_numeric_status(self):
        ret = UploadStatus[self.status].value
        return ret

    def is_preloaded(self):
        return exists(join(self.path, 'preloaded'))


    # ---- These methods must be overriden and implemented by inhering classes for the app to work

    def get_cover_image(self):
        raise NotImplementedError()

    def get_path_to_upload(self):
        raise NotImplementedError()

    def has_slip(self):
        raise NotImplementedError()

    def has_minimal_metadata(self):
        raise NotImplementedError()