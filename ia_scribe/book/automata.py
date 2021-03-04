import datetime, time, logging

from ia_scribe.tasks.book_tasks.upload import upload_book
from ia_scribe.tasks.book_tasks.checks import is_upload_unlocked, has_been_preprocessed_on_cluster, is_it_in_safe_remote_state
from ia_scribe.tasks.book_tasks.packaging import blur_detect, create_imagestack, create_preimage_zip
from ia_scribe.tasks.book_tasks.corrections import upload_book_corrections, upload_book_foldouts
from ia_scribe.tasks.book_tasks.delete import delete_book
from ia_scribe.tasks.book_tasks.metrics import send_rejection

from io import StringIO

from ia_scribe.config.config import Scribe3Configuration
config = Scribe3Configuration()

dashed_string = '*' * 32

def shoulds(book):
    if book.status == 'scribing':
        book.logger.info('move_along:: Book is scribing, nothing to do.')
        return

    if book.status == 'rejected':
        book.logger.info('move_along:: Book has been rejected. Sending metrics and deleting.')
        send_rejection(book)
        return

    if book.status == 'blur_detecting':
        book.logger.info('move_along:: Book is in blur_detecting, calling function...')
        blur_detect(book)
        return

    if book.status == 'create_image_stack':
        book.logger.info('move_along:: Book is in create_image_stack, calling function...')
        create_imagestack(book)
        return

    if book.status == 'create_preimage_zip':
        book.logger.info('move_along:: Book is in create_preimage_zip; doing so...')
        create_preimage_zip(book)
        return

    if book.status == 'upload_started':
        if is_upload_unlocked(book):
            book.logger.info('upload appears unlocked. Proceeding...')
            upload_book(book)
        else:
            book.logger.info('{} is being uploaded'.format(book))
        return

    if book.status == 'corrections_upload_started':
        book.logger.info('move_along:: This book needs some serious corrections upload action.')
        upload_book_corrections(book)
        return

    if book.status == 'uploading_foldouts':
        book.logger.info('move_along:: This book needs some serious foldouts upload action.')
        upload_book_foldouts(book)
        return

    if book.status == 'deleted':
        book.logger.info('move_along:: This book will now be deleted.')
        delete_book(book)
        return

def cans(book):
    '''
    if book.can('do_create_identifier'):
        if not book.has_identifier():
            book.logger.info('move_along:: This book need an identifier. Making one...')
            book.do_create_identifier()
        return
    '''

    # Trigger packaging pipeline
    if book.can('do_begin_packaging'):
        book.logger.info('move_along:: This book is ready for packaging. Beginning pipeline.')
        book.do_begin_packaging()
        return True


    if book.status == 'packaging_started':
        book.logger.info('move_along:: Book is in packaging_started, moving to blur detection stage.')
        if config.is_true('skip_blur_detection'):
            book.do_create_image_stack()
        else:
            book.do_queue_blur_detection()
        return True

    if book.status == 'blur_detection_success':
        book.logger.info('move_along:: Blur detection test passed. Creating image stack...')
        book.do_create_image_stack()
        return True

    if book.status == 'image_stack_created':
        book.logger.info('move_along:: Book is in image_stack_created, moving to create_preimage_zip...')
        book.do_create_preimage_zip()
        return True

    if book.status == 'preimage_zip_created':
        book.logger.info('move_along:: Book is in preimage_zip_created. Packaging is complete.')
        book.do_finish_packaging()
        return True

    if book.can('do_queue_for_upload'):
        book.logger.info('move_along: Looks like I can queue this book for upload. Doing so...')
        book.do_queue_for_upload()
        return True

    if book.status == 'packaging_completed':
        book.logger.info('move_along:: When packaging is complete, we queue for upload.')
        book.do_queue_for_upload()
        return True

    if book.status == 'upload_queued':
        book.do_book_upload_begin()
        return True

    if book.status == 'uploaded':
        if has_been_preprocessed_on_cluster(book):
            book.logger.info('move_along:: Looks like this books was preprocessed on cluster. Will now queue for delete.')
            book.do_upload_book_done()
        return True

    if book.status == 'download_incomplete':
        book.logger.info('move_along: Looks like this is an incomplete download. Deleting.')
        book.do_move_to_trash()
        return True

    if book.status == 'corrected':
        if is_it_in_safe_remote_state(book):
            book.logger.info(
                'move_along:: Looks like this has safely made through the process. Will now actually delete.')
            book.do_move_to_trash()
            return True

    if book.can('do_start_upload_corrections'):
        book.logger.info('move_along:: Uploading corrections')
        book.do_start_upload_corrections()
        return True

    if book.can('do_start_upload_foldouts'):
        book.logger.info('move_along:: Uploading foldouts')
        book.do_start_upload_foldouts()
        return True

    # Trigger deletions
    if book.can('do_delete_staged'):
        book.logger.info('move_along:: Treating staging like trash. Deleting item...')
        book.do_delete_staged()
        return True

    if book.can('do_delete'):
        book.logger.info('move_along:: I can delete!')
        book.do_delete()
        return True

    return False


def move_along_logic(book, upload_queue=None):
    start = time.time()
    book.logger.info('\n{}\nBook engine active at {} on {}'.format(dashed_string,datetime.datetime.now().strftime('%Y%m%d%H%M%S'), book))
    book.logger.info('move_along: Moving status if I can {}'.format(book))
    run_can = cans(book)
    if not run_can:
        book.logger.info('move_along: Running shoulds on {}'.format(book))
        shoulds(book)
    end = time.time()
    book.date_last_updated = end
    book.logger.info('move_along: Done in {} at {}\n{}'.format(end - start, end, dashed_string))


def move_along_core(book, upload_queue):
    try:
        move_along_logic(book, upload_queue)
    except Exception as e:
        book.raise_exception(e)


def move_along(book, upload_queue = None):
   sio = StringIO()
   console = logging.StreamHandler(sio)
   book.logger.addHandler(console)
   exc = None
   try:
       move_along_core(book, upload_queue)
   except Exception as e:
       exc = e
   book.logger.removeHandler(console)
   return console.stream.read(), exc

