from ia_scribe.exceptions import ScribeException
from ia_scribe.ia_services.iabdash import push_event
from ia_scribe.book.book import RepubState

import os, shutil, traceback, json, urllib.request, urllib.parse, urllib.error

def delete_book(item):
    if item.get_type() == 'CD':
        delete_unfinished_book(item)
        return
    if item.has_identifier():
        delete_finished_book(item)
    else:
        delete_unfinished_book(item)

def delete_unfinished_book(book):
    '''Delete a book without checking for remote state

    Called in worker thread
    '''
    try:
        book.logger.debug('Deleting unfinished book')

        payload = {'function': 'delete_unfinished_book',
                   'local_id': book.uuid,
                   'status': book.status}

        shutil.rmtree(book.path)
        book.delete_callback(book)

        push_event('tts-book-deleted', payload,
                   'book', book['path'])
    except ScribeException as e:
        raise e
    except OSError as e:
        return
    except Exception:
        book.logger.error(traceback.format_exc())
        raise ScribeException('Could not delete book!')


def delete_finished_book(book):
    '''

    Called from worker thread.
    '''
    # if book['status'] < UploadStatus.done.value:
    #     return
    book.logger.debug('Checking repub_state for {}'.format(book))
    repub_state = None
    try:
        md_url = ('https://archive.org/metadata/{id}/metadata'
                  .format(id=book['identifier']))
        md = json.load(urllib.request.urlopen(md_url))
    except Exception:
        book.logger.error(traceback.format_exc())
        raise ScribeException('Could not query archive.org for '
                              'repub_state!')
    try:
        if md is None or 'result' not in md:
            print("No repub state or MDAPI unavailable. Continuing with deletion.")

        else:
            repub_state = md['result'].get('repub_state')
            if repub_state is None:
                book.logger.warning('Repub state not found for {}'
                                    .format(book['identifier']))
                return
        if repub_state:
            if int(repub_state) == RepubState.done.value or \
                    RepubState.uploaded.value or \
                    RepubState.post_autocropped.value:
                if os.path.exists(book.path):
                    # User may have already deleted local copy of this book
                    book.logger.info('Deleting {}'.format(book) )
                    payload = {'function': 'delete_finished_book',
                               'local_id': book.uuid,
                               'status': book.status}
                    push_event('tts-book-deleted', payload,
                               'book', book['identifier'])
                    shutil.rmtree(book['path'])
                    book.delete_callback(book)
                else:
                    book.logger.error('UploadWidget: Book not found '
                                 '(could be deleted): {}'.format(book['path']))
            else:
                book.logger.info('Not deleting {} | repub_state={}'
                                  .format(book['path'], repub_state))
        else:
            if os.path.exists(book.path):
                # User may have already deleted local copy of this book
                book.logger.info('Deleting {}'.format(book))
                payload = {'function': 'delete_finished_book',
                           'local_id': book.uuid,
                           'status': book.status}
                push_event('tts-book-deleted', payload,
                           'book', book['identifier'])
                shutil.rmtree(book['path'])
                book.delete_callback(book)
    except ScribeException:
        raise
    except Exception as e:
        book.logger.error(traceback.format_exc())
        raise ScribeException('Could not delete book! {}'.format(e))