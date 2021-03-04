import os
import threading
from functools import reduce
from os.path import join, exists
from enum import Enum
import logging, glob, time
import json
from datetime import datetime

from fysom import *
from ia_scribe.book.states import book_state_machine
from ia_scribe.book.smau import (available_next_actions,
                                 available_next_states,
                                 path_to_success,
                                 path_to_success_corrections,
                                 path_to_deletion,
                                 path_to_state)
from ia_scribe.book.upload_status import status_human_readable
from ia_scribe.utils import all_files_under, ensure_book_directory
from ia_scribe.tasks.book_tasks.identifier import get_identifier_fysom, new_get_identifier
from ia_scribe.tasks.book_tasks.checks \
    import (item_ready_for_upload,\
            verify_uploaded, \
            has_valid_preimage_zip, \
            was_image_stack_processed,
            has_full_imgstack)

from ia_scribe.book.item import Scribe3Item
from ia_scribe.book.scandata import ScanData
from ia_scribe.book.metadata import get_metadata
from ia_scribe.book.upload_status import UploadStatus
from ia_scribe import scribe_globals
from functools import reduce

# Constants to describe files which can exist in book directory
ST_HAS_IDENTIFIER = 1
ST_DOWNLOADED = 2
ST_PRELOADED = 4
ST_HAS_MARC_BIN = 8
ST_HAS_MARC_XML = 16
ST_HAS_METASOURCE = 32
ST_QUEUED_FOR_DELETE = 64
ST_MARC_DOWNLOAD_FAILED = 128  # Doesn't have file representing it

MINIMAL_METADATA = [
            ('title',),
            ('creator',),
            ('isbn',),
            ('scribe3_search_catalog', 'scribe3_search_id'),
        ]
SLIP_METADATA_FILENAME = 'slip_metadata.json'
LOG_FILENAME = 'scanning.log'
IDENTIFIER_NAME = 'identifier.txt'

DEFAULT_STATE = 'uuid_assigned'

class RepubState(Enum):
    # From RePublisherShared.inc
    scan_started = -2
    stub_ready_for_scanning = -1
    uploaded = 10
    autocropped = 11
    failed_autocrop = 12
    post_autocropped = 13
    need_corrections = 14
    rerepublish = 15
    save_for_later = 16
    claimed = 17
    checked_in = 18
    derived = 19
    done = 20
    local = 21
    corrections_sent_to_ttscribe = 31
    book_download_to_ttscribe = 32
    corrections_ready_for_review = 33
    corrections_rejected = 34
    corrections_accepted = 35
    books_has_foldouts = 40
    foldouts_sent_to_station = 41
    foldouts_downloaded_to_station = 42
    foldouts_sent_to_cluster = 43
    safe_delete = 50
    ultimate_delete = 666

def get_upload_target(book):
    book_path = book['path']
    upload_target_status = None
    upload_target_name = None
    if os.path.exists(os.path.join(book_path, 'downloaded')):
        if os.path.exists(os.path.join(book_path, 'foldouts')):
            upload_target_status = UploadStatus.uploading_foldouts
            upload_target_name = 'foldouts'
        elif os.path.exists(os.path.join(book_path, 'foldouts_done')):
            upload_target_status = UploadStatus.uploading_foldouts
            upload_target_name = 'foldouts'
        elif os.path.exists(os.path.join(book_path, 'corrections')):
            upload_target_status = UploadStatus.corrections_upload_queued
            upload_target_name = 'corrections'
        elif os.path.exists(join(book_path, 'reshooting')):
            upload_target_status = UploadStatus.corrections_upload_queued
            upload_target_name = 'corrections'
        else:
            pass
    else:
        upload_target_status = UploadStatus.upload_queued
        upload_target_name = 'local (non downloaded)'

    return upload_target_status, upload_target_name


class Book(Scribe3Item):
    state_machine = book_state_machine

    def __init__(self, book_dict, callback=None, delete_callback=None):
        print("[Book::init()] Creating book object from ->", book_dict)

        super(Book, self).__init__(book_dict, callback, delete_callback)

        self.scandata = ScanData(self.path)
        self.leafs = self.scandata.count_pages()
        self.notes_count = self.scandata.count_notes()

        self.creator = book_dict['creator'] if 'creator' in book_dict else self.metadata[
            'creator'] if 'creator' in self.metadata else None
        self.volume = book_dict['volume'] if 'volume' in book_dict else self.metadata[
            'volume'] if 'volume' in self.metadata else None

        self.shiptracking_id = book_dict['shiptracking'] if 'shiptracking' in book_dict else self.metadata[
            'shiptracking'] if 'shiptracking' in self.metadata else None

        self.boxid = book_dict['boxid'] if 'boxid' in book_dict else self.metadata[
            'boxid'] if 'boxid' in self.metadata else None


    def __repr__(self):
        ret = '<{} is {} ({}-{})'.format(self.uuid,
                                         status_human_readable.get(self.status),
                                         self.status,
                                         UploadStatus[self.status].value, )
        if self.has_identifier():
            ret = ret + '| {}'.format(self.identifier)

        ret = ret + '>'
        return ret

    def reload_metadata(self):
        self.metadata = get_metadata(self.path)
        #self.notes = self.metadata['notes'] if 'notes' in self.metadata else None
        self.shiptracking_id = self.metadata['shiptracking'] if 'shiptracking' in self.metadata else None
        self.boxid = self.metadata['boxid'] if 'boxid' in self.metadata else None
        self.volume = self.metadata['volume'] if 'volume' in self.metadata else None
        super(Book, self).reload_metadata()

    def reload_scandata(self):
        self.scandata = ScanData(self.path)
        self.leafs = self.scandata.count_pages()
        self.notes_count = self.scandata.count_notes()
        self.date_last_updated = self.load_last_modified_from_disk(including_move_along=True)
        self.date_last_modified = self.load_last_modified_from_disk()
        self.date_created = self.load_date_created_from_disk()
        if self.notify:
            self.notify('reloaded_scandata')


    def get_claimer(self):
        path = join(os.path.expanduser(self.path), 'claimer')
        if exists(path):
            with open(path, 'r') as f:
                return f.read() or 'None'
        return 'None'

    def get_scandata(self):
        return self.scandata.dump_raw()

    def as_dict(self):
        ret = super(Book, self).as_dict()
        ret.update({
            'volume': self.volume,
            'notes_count': self.notes_count,
            'leafs': self.leafs,
            'shiptracking': self.shiptracking_id if self.shiptracking_id else '',
            'boxid': self.boxid if self.boxid else '',
        })
        return ret

    def has_minimal_metadata(self, exclude_catalog=False):
        result = []
        for combination in MINIMAL_METADATA:
            if combination == ('scribe3_search_catalog', 'scribe3_search_id'):
                if exclude_catalog:
                    break
            is_combination_satisfied = True
            for really_important_field in combination:
                if really_important_field not in self.metadata:
                    is_combination_satisfied = False
                    break
                if self.metadata[really_important_field] == '':
                    is_combination_satisfied = False
                    break
            result.append(is_combination_satisfied)
        ret = reduce(lambda x, y: x or y, result)
        return ret

    def is_downloaded(self):
        ret = os.path.exists(os.path.join(self.path, 'downloaded'))
        return ret

    def is_modern_book(self):
        return 'scribe3_search_id' in self.metadata

    def is_preloaded(self):
        return exists(join(self.path, 'preloaded'))

    def has_rcs(self):
        REQUIRED_FIELDS_FOR_NATIVE_BOOK = ['sponsor',
                                           'contributor',
                                           'collection',
                                           'rcs_key']
        for field in REQUIRED_FIELDS_FOR_NATIVE_BOOK:
            if field not in self.metadata:
                return False
        return True

    def has_rcs_if_required(self):
        if self.is_preloaded():
            return True
        if self.is_downloaded():
            return True
        # RCS is required
        return self.has_rcs()

    def get_slip(self, full_path = False):
        sliplike_files = glob.glob(os.path.join(self.path, '*slip.png'))
        if len(sliplike_files) == 0:
            return None
        slip_paths= [x for x in sliplike_files]
        slip_paths.sort(key=os.path.getmtime, reverse=True)
        functor = lambda x: x
        if not full_path:
            functor = os.path.basename
        slip_files = [functor(x) for x in slip_paths]
        slip_filename = slip_files[0]
        return slip_filename

    def has_slip(self):
        return self.get_slip() is not None

    def has_slip_if_required(self):
        if self.is_modern_book():
            return self.has_slip() not in [False, None]
        return True

    def get_slip_type(self):
        from ia_scribe.tasks.print_slip import SLIP_IMAGE_NAMES
        filename_to_slip_type = {v: k for k, v in SLIP_IMAGE_NAMES.items()}
        slip_filename = self.get_slip()
        if not slip_filename:
            return None
        slip_file = slip_filename.replace('.png', '')
        if slip_file in list(filename_to_slip_type.keys()):
            return filename_to_slip_type[slip_file]
        else:
            return None

    def get_slip_metadata_file_path(self):
        return join(self.path, SLIP_METADATA_FILENAME)

    def has_slip_metadata_file(self):
        ret = False
        path = self.get_slip_metadata_file_path()
        if exists(path):
            ret = True
        return ret

    def get_slip_metadata(self):
        ret = None
        if self.has_slip() or self.has_slip_metadata_file():
            path = self.get_slip_metadata_file_path()
            with open(path, 'r') as f:
                ret = json.load(f)
        return ret

    def set_slip_metadata(self, type, metadata):
        metadata['type'] = type
        dt = metadata.get('datetime')
        metadata['datetime'] = dt.strftime('%Y%m%d%H%M%S')
        slip_metadata = json.dumps(metadata, indent=4, sort_keys=True)
        with open(self.get_slip_metadata_file_path(), 'w+') as f:
            f.write(slip_metadata)

    def has_full_image_stack(self):
        return has_full_imgstack(self)

    def has_foldout_target_selected(self):
        path = join(self.path, 'send_to_station')
        return os.path.exists(path)

    def get_foldout_target(self):
        if self.has_foldout_target_selected():
            with open(join(self.path, 'send_to_station'), 'r') as f:
                return f.read()
        else:
            return None

    def set_foldout_target(self, scanner):
        with open(join(self.path, 'send_to_station'), 'w+') as f:
            f.write(scanner)

    def has_full_image_stack_wrapper(self, e):
        self.logger.info('checking that {} has a full imgstack...'.format(self.identifier))
        ret, msg = has_full_imgstack(self)
        self.logger.info('Result is {} {}'.format(ret, msg))
        if ret == False:
            self.raise_exception('has_full_imgstack_wrapper', msg)
        return ret

    def item_clear_for_upload_wrapper(self, e):
        self.logger.info('checking that {} is clear for upload'.format(self.identifier))
        ret = item_ready_for_upload(self)
        self.logger.info('Result is {}'.format(ret))
        return ret

    def was_image_stack_processed_wrapper(self, e):
        self.logger.info('checking that imagestack was formed properly')
        ret = was_image_stack_processed(self)
        self.logger.info('Result is {}'.format(ret))
        return ret

    def has_valid_preimage_zip_wrapper(self, e):
        self.logger.info('checking that preimage.zip archive was built properly')
        ret = has_valid_preimage_zip(self)
        self.logger.info('Result is {}'.format(ret))
        return ret

    def has_slip_if_required_wrapper(self, e):
        self.logger.info('checking that a slip is present if required')
        ret = self.has_slip_if_required()
        self.logger.info('Result is {}'.format(ret))
        return ret

    def has_rcs_if_required_wrapper(self, e):
        self.logger.info('checking that a collection string was set for the book')
        ret = self.has_rcs_if_required()
        self.logger.info('Result is {}'.format(ret))
        return ret

    def ok_to_delete(self, e):
        self.logger.info('Checking whether it is safe to delete this book')
        if self.is_downloaded():
            self.logger.info('Book was downloaded, we can go ahead.')
            return True
        else:
            self.logger.info('Book was scanned on this station. Verifying with cluster...')
            return verify_uploaded(self)

    def get_jpegs(self):
        jpegs = sorted(glob.glob(os.path.join(self.path, '[0-9][0-9][0-9][0-9].jpg')))
        return jpegs

    def get_thumb_jpegs(self):
        jpegs = sorted(glob.glob(os.path.join(self.path, 'thumbnails', '[0-9][0-9][0-9][0-9].jpg')))
        return jpegs

    def get_imagestack(self):
        jp2s = sorted(glob.glob(os.path.join(self.path, '[0-9][0-9][0-9][0-9].jp2')))
        if len(jp2s) == 0:
            jp2s = self.get_jpegs()
        return jp2s

    def get_path_to_upload(self, human_readable=False):
        return_value = []
        if self.get_numeric_status() >= 888:
            return return_value
        if self.get_numeric_status() < 797:
            return_value = path_to_success(self.status)
        else:
            return_value = path_to_success_corrections(self.status)
        if human_readable:
            return_value = self.humanify(return_value)
        return return_value


    def set_force_upload(self):
        self.force_upload = True

    def build_callbacks(self):
        ret = {
            'onchangestate': self._on_change_state,
            'onbeforedo_create_identifier': get_identifier_fysom,
            # 'onbeforedo_queue_processing': partial(self.set_checkpoint, 'processing_queued'),
            # 'onbeforedo_queue_for_upload': partial(self.set_checkpoint, 'upload_queued'),
            # 'onbeforedo_move_to_trash': partial(self.set_checkpoint, 'delete_queued'),
            # 'create_metadata': partial(make_identifier, self, self)
            # 'ondo_begin_packaging': package_book,
            # 'ondo_create_image_stack': create_imagestack,
            # 'ondo_finish_image_stack': create_preimage_zip,
            #  'ondo_queue_for_upload': upload_book,
            # 'onafterdo_upload_book_done': verify_uploaded,
        }
        return ret

    def is_folio(self):
        ret = self.metadata.get('source') == 'folio'
        return ret

    def get_cover_image(self):
        if self.is_folio():
            ret = os.path.join(self.path, 'thumbnails', '0002.jpg')
        else:
            ret = os.path.join(self.path, 'thumbnails', '0001.jpg')
        return ret

    GSM = FysomGlobal(
        cfg=book_state_machine,
        state_field='status',
    )
