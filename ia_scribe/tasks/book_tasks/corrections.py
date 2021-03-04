import os
import copy
from os.path import join
import re
import json
import requests
from datetime import datetime
from PIL import Image
from ia_scribe.book.book import RepubState

from ia_scribe.book.scandata import ScanData
from ia_scribe.ia_services.iabdash import push_event
from ia_scribe.tasks.book_tasks.petabox import get_pending_catalog_tasks
from ia_scribe.ia_services.btserver import get_ia_session, get_scanner_item

from ia_scribe.exceptions import ScribeException

def _remove_book_from_btserver_item(book, Logger):
    try:
        Logger.debug('Acquiring btserver item')
        ttscribe_item = get_scanner_item()
        Logger.debug('Removing book from tts list')
        btserver_list = (ttscribe_item.metadata['books'][1:-1]
                         .split(','))
        original_btserver_list = [x.strip() for x in btserver_list]
        original_btserver_list.remove(book.identifier)
        updated_btserver_list = (str(original_btserver_list)
                                 .replace("'", "").replace(' ', ''))
        ttscribe_item.modify_metadata({'books': updated_btserver_list})
    except Exception as e:
        Logger.error("_remove_book_from_btserver_item: Error {}".format(e))
        '''we don't let a corrections upload fail because the book wasn't 
        removed from the btserver item list.'''
        pass


def _create_scandata(book, book_folder, foldouts, Logger):
    scandata = json.loads(ScanData(book['path']).dump())
    cdic = {}
    tdic = {}
    rdic = {}
    rtdic = {}
    '''
    This subprogram uploads a corrected book back to republisher.
    It:
    - Verifies that the book was downloaded.
    - Gets ahold of the tts identifier to later remove the book from the 
        item's "books" list.
    - Constructs and maintains four dictionaries: new pages (cdic), new 
        pages thumbs (tdic), reshot pages(rdic), reshot pages thumbs 
        (rtdic) that will later become the scandata.
    -- Looks for new pages (spreads insertions and/or appends) and their 
        thumbs
    -- Add republisher tags (that's what post-processing would do)
    -- Looks for replacements (in bookpath/reshooting) if present
    -- saves a scandata_rerepublished.json
    - Uploads the pictures and scandatas
    - Updates tts item, repub state and metrics
    '''

    # Here we add the new pages

    # cdic is the corrections dictionary, and it contains entries in the
    # form:
    #
    # {item path : local path } - for example:
    # {'corrections/0044.jpg' : '~/scribe_books/1234/0022.jpg'}
    try:
        cdic = {book_folder + '/' + k: os.path.join(book['path'], k)
                for k in next(os.walk(book['path']))[2]
                if re.match('\d{4}\.jpg$', os.path.basename(k))}
        # And the thumbs from the new pages
        # REMOVE THUMB FROM OS WALK PATH
        tdic = {book_folder + '/thumbnails/' + k:
                    os.path.join(book['path'], 'thumbnails', k)
                for k in next(os.walk(join(book['path'])))[2]
                if re.match('\d{4}\.jpg$', os.path.basename(k))}
    except Exception:
        Logger.error('_create_scandata: No corrections found.')

    # Ensure the scandata has the appropriate tags for re-republishing

    # NEW PAGES DICT
    Logger.debug('_create_scandata: Processing new pages...')
    for k in cdic:
        page_num = str(int(k.split('.jpg')[0].split('/')[1]))
        Logger.debug('_create_scandata: Processing page {}'.format(page_num))
        try:
            page_data_exists = scandata['pageData'][page_num] is not None
            Logger.debug('_create_scandata: Page data for page {} exists in '
                         'scandata'.format(page_num))
        except Exception as e:
            raise ScribeException(e)

        # Rotate images
        im = Image.open(cdic[k])
        # im = im.rotate(
        #     int(scandata['pageData'][page_num]['rotateDegree'])
        # )
        width, height = im.size

        # scandata['pageData'][page_num]['rotateDegree'] = 0
        if abs(int(scandata['pageData'][page_num]['rotateDegree'])) in [0, 180]:
            scandata['pageData'][page_num]['origWidth'] = str(width)
            scandata['pageData'][page_num]['origHeight'] = str(height)
        elif abs(int(scandata['pageData'][page_num]['rotateDegree'])) in [90, 270]:
            scandata['pageData'][page_num]['origWidth'] = str(height)
            scandata['pageData'][page_num]['origHeight'] = str(width)

        Logger.debug('\n\n\n ---->>> CORRECTIONS DEBUG - PAGE INSERT- '
                     'please report this \n\n')
        Logger.debug(
            'rotatedegree={2}, origWidth={0}, height={1}'
                .format(scandata['pageData'][page_num]['origWidth'],
                        scandata['pageData'][page_num]['origHeight'],
                        scandata['pageData'][page_num]['rotateDegree'])
        )
        Logger.debug('<<<---- END CORRECTIONS DEBUG - - - - - - - -\n\n\n')

        scandata['pageData'][page_num]['origFileName'] = k.split('/')[1]
        scandata['pageData'][page_num]['sourceFileName'] = k
        scandata['pageData'][page_num]['proxyFullFileName'] = k
        if not foldouts:
            scandata['pageData'][page_num]['correctionType'] = 'INSERT'
            scandata['pageData'][page_num]['TTSflag'] = 0

        Logger.debug('\n\n\n ---->>> CORRECTIONS DEBUG - please report '
                     'this \n\n')
        Logger.debug('\n' + str(scandata['pageData'][page_num]))
        Logger.debug('<<<---- END CORRECTIONS DEBUG - - - - - - - -\n\n\n')
    # THUMBS FOR NEW PAGES
    for k in tdic:
        page_num = str(int(k.split('.jpg')[0].split('/')[2]))
        scandata['pageData'][page_num]['proxyFileName'] = k

    Logger.debug('_create_scandata: Processed {} new images.'.format(len(cdic)))

    try:
        # here we add the reshot images
        rdic = {
            book_folder + '/' + k: join(book['path'], 'reshooting', k)
            for k in next(os.walk(join(book['path'], 'reshooting')))[2]
            if re.match('\d{4}\.jpg$', os.path.basename(k))
        }

        # RESHOT IMAGES DICT
        for k in rdic:
            page_num = str(int(k.split('.jpg')[0].split('/')[1]))
            # rotate images
            im = Image.open(rdic[k])
            # im = im.rotate(
            #     int(scandata['pageData'][page_num]['rotateDegree'])
            # )
            width, height = im.size
            # im.save(rdic[k])

            # scandata['pageData'][page_num]['rotateDegree'] = 0
            if abs(int(scandata['pageData'][page_num]['rotateDegree'])) in [0, 180]:
                scandata['pageData'][page_num]['origWidth'] = str(width)
                scandata['pageData'][page_num]['origHeight'] = str(height)
            elif abs(int(scandata['pageData'][page_num]['rotateDegree'])) in [90, 270]:
                scandata['pageData'][page_num]['origWidth'] = str(height)
                scandata['pageData'][page_num]['origHeight'] = str(width)

            Logger.debug('---->>> CORRECTIONS DEBUG - PAGE RESHOOT')
            Logger.debug(
                'rotatedegree is {2}, origWidth = {0}, height= {1}'
                    .format(scandata['pageData'][page_num]['origWidth'],
                            scandata['pageData'][page_num]['origHeight'],
                            scandata['pageData'][page_num]['rotateDegree'])
            )
            Logger.debug('<<<---- END CORRECTIONS DEBUG - - - - - - - - -')

            scandata['pageData'][page_num]['origFileName'] = k.split('/')[1]
            scandata['pageData'][page_num]['sourceFileName'] = k
            scandata['pageData'][page_num]['correctionType'] = 'REPLACE'
            scandata['pageData'][page_num]['proxyFullFileName'] = k
            scandata['pageData'][page_num]['TTSflag'] = 0

            Logger.debug('---->>> CORRECTIONS DEBUG - please report this')
            Logger.debug('\n' + str(scandata['pageData'][page_num]))
            Logger.debug('<<<---- END CORRECTIONS DEBUG - - - - - - - -')

        # here we add the thumbs from the reshooting
        rtdic = {
            book_folder + '/thumbnails/' + k: join(book['path'], 'reshooting', 'thumbnails', k)
            for k in next(os.walk(join(book['path'], 'reshooting', 'thumbnails')))[2]
            if re.match('\d{4}\.jpg$', os.path.basename(k))
        }

        # THUMBS FOR RESHOT IMAGES
        for k in rtdic:
            page_num = str(int(k.split('.jpg')[0].split('/')[2]))
            scandata['pageData'][page_num]['proxyFileName'] = k

        Logger.debug('_create_scandata: Processed {} reshot images.'.format(len(rdic)))

    except Exception as e:
        Logger.exception('_create_scandata: No reshot pages found')

    # Super Solenoid Scandata from disk (page info)
    sss = {int(k): v for k, v in list(scandata['pageData'].items())}
    # Now we want our own piece of memory for this one
    new_scandata = copy.deepcopy(scandata)
    new_scandata['pageData'] = {}
    new_scandata['pageData']['page'] = []

    # Rewrite pages section

    Logger.debug('_create_scandata: Adding all computed pages to new scandata...')
    for page in sorted(sss):
        Logger.debug('_create_scandata: {}'.format(page))
        sss[page]['leafNum'] = page
        try:
            pnum = sss[page]['pageNumber']['num']
            sss[page]['pageNumber'] = pnum
        except Exception:
            pass
        new_scandata['pageData']['page'].append(sss[page])

    # Rewrite assertions to be compatible with republisher

    try:
        Logger.debug('\nNow rewriting page assertions for repub compatibility '
                     'if present')
        temp_pageNumData = copy.deepcopy(scandata['bookData']['pageNumData'])
        temp_pageNumData['assertion'] = []
        for entry in scandata['bookData']['pageNumData']:
            if entry.isdigit():
                del temp_pageNumData[entry]

        for assertion in scandata['bookData']['pageNumData'].items():
            temp_assertion = {'leafNum': str(assertion[0]),
                              'pageNum': str(assertion[1])}
            temp_pageNumData['assertion'].append(temp_assertion)

        Logger.debug('_create_scandata: OK done. New pageNumData block: {}'
                     .format(temp_pageNumData))

        new_scandata['bookData']['pageNumData'] = temp_pageNumData
    except Exception as e:
        Logger.exception('_create_scandata: No pageNumData block found or error processing '
                         'it.: '.format(e))

    # Write it all to file
    with open(join(book['path'], 'scandata_rerepublished.json'), 'w+') as outfile:
        json.dump(new_scandata, outfile)

    Logger.debug('_create_scandata: Done constructing scandata.')
    return cdic, tdic, rdic, rtdic

def _check_preconditions(book, book_item, Logger):
    if not os.path.exists(os.path.join(book['path'], 'downloaded')):
        raise ScribeException('_check_preconditions: Cannot use this upload function on a book '
                              'that was not downloaded')

    if book_item.metadata['repub_state'] not in ['32', '42']:
        raise ScribeException('_check_preconditions: Book is not in correct remote repub_state: aborting upload.')

    outstanding_catalog_tasks, outstanding_catalog_tasks_list = get_pending_catalog_tasks(book_item.identifier)

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
        raise ScribeException(msg)

def _change_repub_state(book_item, target_repub_state):
    res_repub_state_change = None
    res_repub_state_change = book_item.modify_metadata({'repub_state': target_repub_state})

    if res_repub_state_change is None or res_repub_state_change.status_code != 200:
        raise ScribeException('Received erroneous response: {}'.format(res_repub_state_change))
    elif res_repub_state_change.status_code == 200:
        if res_repub_state_change.text:
            response = json.loads(res_repub_state_change.text)
            if 'error' in response:
                raise ScribeException('Metadata API courteously '
                                      'tucked an error in a valid response.'
                                      '\nWhat seems to have gone wrong is {}'
                                      .format(str(response['error'])))

def upload_book_corrections(book):
    try:
        Logger = book.logger
        Logger.info('upload_book_corrections: Uploading corrections for book '
                    '{}'.format(book))

        ia_session = get_ia_session()
        book_item = ia_session.get_item(book['identifier'], )

        _check_preconditions(book, book_item, Logger)

        book_folder = 'corrections'

        cdic, tdic, rdic, rtdic = _create_scandata(book, book_folder, False, Logger)

        responses = []
        # Upload the pictures
        Logger.debug('upload_book_corrections: Uploading pics')
        if cdic != {}:
            res = book_item.upload(cdic, retries=10, verify=True,
                                   retries_sleep=60, queue_derive=False)
            responses.append(res)

        if tdic != {}:
            res = book_item.upload(tdic, retries=10, verify=True,
                                   retries_sleep=60, queue_derive=False)
            responses.append(res)

        try:
            if rdic != {}:
                res = book_item.upload(rdic, retries=10, verify=True,
                                       retries_sleep=60, queue_derive=False)
                responses.append(res)

            if rtdic != {}:
                res = book_item.upload(rtdic, retries=10, verify=True,
                                       retries_sleep=60, queue_derive=False)
                responses.append(res)
        except requests.exceptions.ConnectionError as e:
            Logger.error(
                'upload_book_corrections: Connection exception {} '
                'has occurred at rdic upload time; aborting!'.format(str(e)))
            raise e
        except Exception as e:
            Logger.error('upload_book_corrections: Error {} has occurred at rdic upload time'.format(e))
            raise e

        Logger.debug('upload_book_corrections: Done. Uploading scandata...')
        # Upload the scandata
        target_scandata = 'corrections/scandata.json'

        scandata = join(book['path'], 'scandata_rerepublished.json')
        upload_res = book_item.upload({target_scandata: scandata},
                                      retries=10,
                                      retries_sleep=60,
                                      queue_derive=False,
                                      verify=True,)

        if os.path.exists(os.path.join(book['path'], 'scanning.log')):
            book.logger.debug(
                'Uploading Scanning log file'
            )
            upload_name_mapping = \
                {'logs/' + book['identifier']
                 + '_scanning_{:%Y-%m-%d%H:%M:%S}.log'.format(datetime.now()):
                     join(book['path'], 'scanning.log')}
            response = book_item.upload(upload_name_mapping, retries=10,
                                   retries_sleep=60, queue_derive=False, verbose=True,
                                        verify=True,)
            responses.append(response)
            url_to_status_code = \
                {r.request.url: r.status_code for r in response}
            book.logger.debug('Response from upload: {} | {}'
                              .format(response, url_to_status_code))

        responses.append(upload_res)
        # corrections_uploaded

        # flatten responses list:
        flat_responses = [y for x in responses for y in x]
        for response in flat_responses:
            Logger.info('{} returned {}'.format(response.url, response.status_code))
            if response.status_code != 200:
                raise Exception('upload_book_corrections: Response code {} {} - {} from cluster. '
                                'URL was: {} | content: {}'
                                'This is an error. Upload will be attempted again.'
                                .format(response.status_code,
                                        response.reason,
                                        response.text if 'text' in response else "",
                                        response.url,
                                        response.content))

        Logger.debug('Done. Changing repub state...')

        _change_repub_state(book_item, 33)
        _remove_book_from_btserver_item(book, Logger)

        book.do_upload_corrections_done()

        payload = {
            'repub_state': RepubState.corrections_ready_for_review.value,
            'responses': flat_responses,

        }
        push_event('tts-book-corrections-sent', payload,
                   'book', book['identifier'])
        Logger.debug('All done.')
        return

    except requests.ConnectionError as e:
        raise ScribeException('Upload Failed. Please check network and '
                              'S3 Keys (Error was: {})'.format(e))
    except Exception as e:
        book.do_upload_corrections_fail()
        book.raise_exception(e)

def upload_book_foldouts(book,):
    try:
        Logger = book.logger
        Logger.info('upload_book_foldouts: Uploading foldouts for book '
                    '{}'.format(book))

        ia_session = get_ia_session()
        book_item = ia_session.get_item(book['identifier'], )

        _check_preconditions(book, book_item, Logger)

        book_folder = 'foldouts'

        cdic, tdic, rdic, rtdic = _create_scandata(book, book_folder, True, Logger)

        responses = []
        # Upload the pictures
        Logger.debug('upload_book_foldouts: Uploading pics')
        book.update_message('Foldouts upload | Images')
        if cdic != {}:
            res = book_item.upload(cdic, retries=10, verify=True,
                                   retries_sleep=60, queue_derive=False)
            responses.append(res)

        if tdic != {}:
            res = book_item.upload(tdic, retries=10, verify=True,
                                   retries_sleep=60, queue_derive=False)
            responses.append(res)

        try:
            if rdic != {}:
                res = book_item.upload(rdic, retries=10, verify=True,
                                       retries_sleep=60, queue_derive=False)
                responses.append(res)

            if rtdic != {}:
                res = book_item.upload(rtdic, retries=10, verify=True,
                                       retries_sleep=60, queue_derive=False)
                responses.append(res)
        except requests.exceptions.ConnectionError as e:
            Logger.error(
                'upload_book_foldouts: Connection exception {} '
                'has occurred at rdic upload time; aborting!'.format(str(e)))
            raise e
        except Exception as e:
            Logger.error('upload_book_foldouts: Error {} has occurred at rdic upload time'.format(e))
            raise e

        Logger.debug('upload_book_foldouts: Done. Uploading scandata...')
        # Upload the scandata

        target_scandata = 'scandata.json'
        book.update_message('Foldouts upload | Scandata')
        scandata = join(book['path'], 'scandata_rerepublished.json')
        upload_res = book_item.upload({target_scandata: scandata},
                                      retries=10,
                                      retries_sleep=60,
                                      queue_derive=False,
                                      verify=True,)

        if os.path.exists(os.path.join(book['path'], 'scanning.log')):
            book.update_message('Foldouts upload | Log')
            book.logger.debug(
                'Uploading Scanning log file'
            )
            upload_name_mapping = \
                {'logs/' + book['identifier']
                 + '_scanning_{:%Y-%m-%d%H:%M:%S}.log'.format(datetime.now()):
                     join(book['path'], 'scanning.log')}
            response = book_item.upload(upload_name_mapping, retries=10,
                                   retries_sleep=60, queue_derive=False, verbose=True,verify=True, )
            responses.append(response)
            url_to_status_code = \
                {r.request.url: r.status_code for r in response}
            book.logger.debug('Response from upload: {} | {}'
                              .format(response, url_to_status_code))

        responses.append(upload_res)
        # corrections_uploaded

        # flatten responses list:
        flat_responses = [y for x in responses for y in x]
        for response in flat_responses:
            Logger.info('{} returned {}'.format(response.url, response.status_code))
            if response.status_code != 200:
                raise Exception('upload_book_foldouts: Response code {} {} - {} from cluster. '
                                'URL was: {} | content: {}'
                                'This is an error. Upload will be attempted again.'
                                .format(response.status_code,
                                        response.reason,
                                        response.text if 'text' in response else "",
                                        response.url,
                                        response.content))

        Logger.debug('Done. Changing repub state...')

        _change_repub_state(book_item, 43)

        _remove_book_from_btserver_item(book, Logger)

        book.do_upload_foldouts_done()

        payload = {
            'repub_state': 43,
            'responses': flat_responses,

        }
        push_event('tts-book-corrections-sent', payload,
                   'book', book['identifier'])
        Logger.debug('All done.')

        return

    except requests.ConnectionError as e:
        raise ScribeException('Upload Failed. Please check network and '
                              'S3 Keys (Error was: {})'.format(e))
    except Exception as e:
        book.do_upload_foldouts_fail()
        book.raise_exception(e)


