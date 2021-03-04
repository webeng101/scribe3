import os, traceback
from datetime import datetime, timedelta
from lxml import etree
from zipfile import ZipFile

from os.path import join
from ia_scribe.book.scandata import ScanData
from ia_scribe.tasks.book_tasks.petabox import get_pending_catalog_tasks, get_repub_state
from ia_scribe.tasks.book_tasks.upload import _check_preimage_is_valid
from ia_scribe.exceptions import ScribeException
from ia_scribe.ia_services.btserver import get_ia_session
from ia_scribe import scribe_globals
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.tasks.metadata import ALLOWED_FILE_NAMES, ALLOWED_VARIABLE_FILE_NAMES

config = Scribe3Configuration()

def has_been_preprocessed_on_cluster(book):
    current_repub_state = get_repub_state(book)
    return current_repub_state >= 12

def is_it_in_safe_remote_state(book):
    current_repub_state = get_repub_state(book)
    res = current_repub_state in scribe_globals.SAFE_REPUB_STATES
    return res

# PORTED
def has_full_imgstack(book, foldout=False):
    book.logger.info('has_full_imgstack: Init')
    book_path = book.path
    book.reload_scandata()
    scandata = book.scandata
    if not (book_path and scandata):
        return False, 'Cover image is missing!'
    max_leaf_number = scandata.get_max_leaf_number()
    if max_leaf_number is None or max_leaf_number < 1:
        return False, 'Cover image is missing'
    for leaf_number in range(max_leaf_number + 1):
        leaf_data = scandata.get_page_data(leaf_number)
        image_path = os.path.join(book_path, '{:04d}.jpg'.format(leaf_number))
        if not (leaf_data and os.path.exists(image_path)):
            if leaf_number == 0 or leaf_number == 1:
                return False, 'Cover image is missing!'
            return False, 'Image #{} is missing'.format(leaf_number)
    '''
    if max_leaf_number % 2 == 0:
        if foldout:
            msg = 'packaging.has_full_imgstack: yes because single-camera mode was detected'
            return True, msg
        else:
            return False, 'Image #{} is missing!'.format(max_leaf_number + 1)
    '''
    return True, None

def has_valid_preimage_zip(book):
    zipfile_list = None
    zip_path = _check_preimage_is_valid(book)
    with ZipFile(zip_path, 'r') as preimage_zip:
        zipfile_list = preimage_zip.namelist()
    image_files_in_preimage_zip = [x.split('.jp')[0][-4:] for x in zipfile_list]
    for item in book.get_jpegs():
        original_filename = item.split('.jpg')[0][-4:]
        assert original_filename in image_files_in_preimage_zip
    return True

def was_image_stack_processed(book):
    #here also check that file lengths are non-zero
    return len(book.get_jpegs()) == len(book.get_imagestack())

# PORTED
def is_upload_unlocked(book):
    upload_lock = os.path.join(book.path, "upload_lock")
    if os.path.exists(upload_lock):
        current_pid = os.getpid()
        upload_pid = None
        with open(upload_lock) as f:
            upload_pid = f.read()

        if str(upload_pid) == str(current_pid):
            book.logger.info("MultiUploadChecker: Item {} is uploading, skipping...".format(book))
            return False
        else:
            book.logger.info(
                "MultiUploadChecker: Item {} looks like a botched upload, re-queuing...".format(book))
            os.remove(upload_lock)
            return True
    else:
        book.logger.info("MultiUploadChecker: Item {} looks clear for upload".format(book))
        return True

# PORTED
def verify_uploaded(book):

    ia_session = get_ia_session()

    book.logger.info('verify_uploaded: Verifying {} was uploaded to the cluster.'.format(book))

    # we do have identifier in the book dictionary, but we only trust
    # what's on the drive for this one
    identifier = book.identifier
    if not identifier:
        book.logger.info('verify_uploaded: No identifier.txt. Assuming empty book and deleting.'.format(book))
        return True

    book.logger.info('verify_uploaded: Read {} from identifier.txt.'.format(book))

    # gather data

    i = ia_session.get_item(identifier)

    repub_state = int(i.metadata['repub_state']) if 'repub_state' in i.metadata else None
    book.logger.info('verify_uploaded: repub_state {}'.format(repub_state))

    scandate = datetime.strptime(i.metadata['scandate'], '%Y%m%d%H%M%S') if 'scandate' in i.metadata else None
    book.logger.info('verify_uploaded: scandate {}'.format(scandate))

    #scanner = i.metadata['scanner'] if 'scanner' in i.metadata else None
    #book.logger.info('verify_uploaded: scanner {}'.format(scanner))
    #this_scanner = config.get('identifier', 0)

    tasks_running, tasks_list = get_pending_catalog_tasks(i)
    book.logger.info('verify_uploaded: pending book_tasks {}'.format(tasks_running))

    local_imgcount = int(ScanData(book.path).count_pages())
    remote_imgcount = int(i.metadata['imagecount']) if 'imagecount' in i.metadata else None
    book.logger.info('verify_uploaded: local pages: {} '
                '| remote pages: {}'.format(local_imgcount, remote_imgcount))

    # These are here so you can bypass one easily by setting it to True
    scandate_ok = False
    repub_state_ok = False
    tasks_running_ok = False
    #scanner_ok = False
    imgcount_ok = True

    # policies
    if not repub_state:
        repub_state_ok = True
    elif repub_state > 10:
        repub_state_ok = True

    threshold = config.get_numeric_or_none('defer_delete_by')
    if threshold and scandate:
        if not datetime.now() - timedelta(hours=threshold) <= scandate <= datetime.now():
            scandate_ok = True
    else:
        # If the user doesn't specify a value, delete immediately
        scandate_ok = True

    if tasks_running == 0:
        tasks_running_ok = True

    if remote_imgcount:
        if local_imgcount == remote_imgcount:
            imgcount_ok = True
    else:
        imgcount_ok = True

    # aggregate and return
    ret = scandate_ok \
          and repub_state_ok and tasks_running_ok \
          and imgcount_ok

    if book.force_delete:
        ret = True

    book.logger.info('verify_uploaded: Do selectors allow for deletion?'
                ' scandate ok: {} |  repub_state_ok {} '
                '|  book_tasks ok: {} | imgcount_ok: {} | Force delete: {}-->>> '
                'VERDICT: {}'.format(scandate_ok,
                                     repub_state_ok, tasks_running_ok, imgcount_ok, book.force_delete, ret))

    return ret

# PORTED
def item_ready_for_upload(book):
    '''Book items might have already been preloaded with metadata in the
    IA scan process. However, prevent uploading to ia items which already
    have images uploaded.

    Called in worker thread.
    '''

    try:
        session= get_ia_session()
        item = session.get_item(book.identifier)

        if not item.exists:
            if book:
                preloaded_path = os.path.join(book.path, 'preloaded')
                if os.path.exists(preloaded_path):
                    # This item was created in offline mode, but the
                    # identifier doesn't exist
                    book.logger.error('Item {0} is tagged as preloaded, but '
                                 'the identifier does not exist. Aborting '
                                 'upload and reverting to scribing '
                                 'status.'.format(book.identifier))
                    return False
                else:
                    book.logger.info('Item does not exist and user wants to '
                                'upload to item {0}. Ok\'ing that'
                                .format(book.identifier))
                    # no existing item, so safe to use this identifier
                    return True
        allowed_formats = {'Metadata', 'MARC', 'MARC Source',
                           'MARC Binary', 'Dublin Core',
                           'Archive BitTorrent', 'Web ARChive GZ',
                           'Web ARChive', 'Log', 'OCLC xISBN JSON',
                           'Internet Archive ARC',
                           'Internet Archive ARC GZ', 'CDX Index',
                           'Item CDX Index', 'Item CDX Meta-Index',
                           'WARC CDX Index', 'Metadata Log'}

        ALLOWED_ITEM_FILE_NAMES = ['{}_{}'.format(book.identifier, x)
                                   for x in ALLOWED_VARIABLE_FILE_NAMES]

        for item_file_metadata in item.files:
            if item_file_metadata['format'] not in allowed_formats:
                # Ignore new style in-item thumb files
                if item_file_metadata['name'] in ALLOWED_FILE_NAMES:
                    book.logger.info('File {} ({}) is present in '
                                'remote item and allowed: continuing...'.format(
                        item_file_metadata['name'], item_file_metadata['format']))
                    continue
                elif item_file_metadata['name'] in ALLOWED_ITEM_FILE_NAMES:
                    continue
                # files have already been uploaded to this item
                book.logger.error('File {} in item {} is blocking upload.'
                             .format(item_file_metadata, item.identifier))
                return False

    except Exception:
        book.logger.error(traceback.format_exc())
        raise ScribeException('Could not check status of IA item {}'
                              .format(book.identifier))

    return True



def check_rescribing_began(self, book):
    Logger = self.logger
    a = os.path.join(book['path'], 'reshooting')
    try:
        reshooting_files = \
            next(os.walk(os.path.join(book['path'], 'reshooting')))[2]
        return bool(reshooting_files)
    except Exception:
        Logger.exception('UploadWidget: An exception has occurred whilst '
                         'checking whether rescribing has begun. '
                         'Assuming no.')
        return False


def check_foldouts_began(self, book):
    Logger = self.logger
    # if there are files in the root directory that are JPGs, then reshooting has begun
    book_path = os.path.expanduser(book['path'])
    try:
        for fname in os.listdir(book_path):
            if fname.endswith('.jpg'):
                return True
        else:
            return False
    except Exception:
        Logger.exception('UploadWidget: An exception has occurred whilst '
                         'checking whether fodlouts reshooting has begun. '
                         'Assuming no.')
        return False


def is_rescribe_complete(book, Logger):
    book_path = book['path']
    # falling back to scandata xml, TODO: use scandata.json
    tree_path = join(book_path, 'scandata.xml')

    for fname in os.listdir(book_path):
        if fname.endswith('.jpg'):
            Logger.info("FOUND INSERTS, this is no longer just a corrections item")
            return True

    try:
        if not os.path.isfile(tree_path):
            raise IOError('File not found {}'.format(tree_path))
        pages = [elem for event, elem in etree.iterparse(tree_path)
                 if event == 'end' and elem.tag == 'page']
    except Exception:
        Logger.exception('ReScribeScreen: Corrections are not present '
                         'for book: {}'.format(book))
        return False
    # Iterate over the pages and check that
    # all tts-flagged pages have a matching image
    for item in pages:
        if item.find('note') is None:
            continue
        if (item.find('note').text is not None
                and item.find('TTSflag').text == '1'):
            leaf_number = int(item.attrib['leafNum'])
            image_name = '{:04d}.jpg'.format(leaf_number)
            path = join(book_path, 'reshooting', image_name)
            if not os.path.exists(path):
                return False
    return True
