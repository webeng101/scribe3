import os, requests, json
from uuid import uuid4

from ia_scribe.book.scandata import ScanData
from ia_scribe.tasks.book_tasks import helpers as book_helpers
from ia_scribe.ia_services.iabdash import push_event
from ia_scribe.notifications.notifications_manager import NotificationManager
from ia_scribe.ia_services.btserver import get_ia_session
from ia_scribe import scribe_globals
from ia_scribe.ia_services import btserver

from ia_scribe.tasks.task_base import TaskBase, CANCELLED_WITH_ERROR
from ia_scribe.tasks.meta import MetaSchedulerTask

class DownloadBookTask(TaskBase):

    def __init__(self, **kwargs):
        super(DownloadBookTask, self).__init__(**kwargs)
        self._book = None
        self._priority = 'medium'
        self._library = kwargs['library']
        self.identifier = kwargs['identifier']
        self.logger.info('Download books: Downloading {}'.format(self.identifier))
        self.notifications_manager = NotificationManager()
        self._download_type = None


    def create_pipeline(self):
        return [
            self._get_ia_session,
            self._load_item,
            self._validate_repub_state,
            self._create_stub_book,
            self._load_book_metadata,
            self._create_files,
            self._create_scandata,
            self._get_checkout_information,
            self._write_claimer_file,
            self._download_proxies,
            self._set_states,
            self._release_lock,
            self._send_stats,
        ]

    def handle_event(self, event_name, *args, **kwargs):
        if event_name == 'on_state' and self.state == CANCELLED_WITH_ERROR:
            if self._book:
                self._book.do_move_to_trash()
                self._book.do_delete_anyway()

    def _get_ia_session(self):
        self.dispatch_progress('Getting IA session')
        self._ia_session = get_ia_session()

    def _load_item(self):
        self.dispatch_progress('Loading item')
        try:
            self.item = self._ia_session.get_item(self.identifier)
            assert self.item.metadata['repub_state'] is not None
        except Exception as e:
            self.logger.error('No repub_state or item darkened. Skipping...')
            raise e
        self.logger.info('Download book: target item: {} (repub_state = {})'
                    .format(self.item.identifier,
                            self.item.metadata['repub_state']))

    def _validate_repub_state(self):
        self.dispatch_progress('Validating repub state')
        is_repub_state_valid = lambda x: int(x.metadata['repub_state']) in scribe_globals.ALLOWED_DOWNLOAD_REPUB_STATES
        self.logger.info('Validating repub_state {}'.format(int(self.item.metadata['repub_state'])))

        if not is_repub_state_valid(self.item):
            msg = 'Download book: Repub state is not 31 or 34 or 41' \
                  '(is {1}), refusing to download item {0}' \
                .format(self.item.identifier, self.item.metadata['repub_state'])
            self.logger.error(msg)
            raise Exception(msg)

    def _create_stub_book(self):
        self.dispatch_progress('Creating local book')
        message = "This books is being downloaded and no actions are available just yet."
        book_id = str(uuid4())
        self._book = self._library.new_book(book_id, status='download_incomplete', error=message)
        self._book.set_lock()
        self._book.logger.info('Download book: Created stub book {}'.format(self._book))

    def _load_book_metadata(self):
        self.dispatch_progress('Loading metadata')
        md_url = ('https://{}/RePublisher/RePublisher-viewScanData.php'
                  '?id={}'.format(self.item.d1, self.identifier))
        self._md = requests.get(md_url, timeout=5)
        self._book.logger.info('Download book: Fetch scandata from cluster: {}'.format(self._md.status_code))

    def _create_files(self):
        self.dispatch_progress('Downloading files')
        ret = []
        with open(os.path.join(self._book.path, 'identifier.txt'), 'w+') as fp:
            fp.write(self.item.identifier)
        ret.append(fp.name)
        self._book.logger.info('Download book: Created {}'.format(fp.name))

        with open(os.path.join(self._book.path, 'downloaded'), 'w+') as fp:
            fp.write('True')
            ret.append(fp.name)
        self._book.logger.info('Download book: Created {}'.format(fp.name))

        with open(os.path.join(self._book.path, 'uuid'), 'w+') as fp:
            fp.write(self._book.uuid)
        ret.append(fp.name)
        self._book.logger.info('Download book: Created {}'.format(fp.name))

        with open(os.path.join(self._book.path, 'scandata.xml'), 'w+') as fp:
            fp.write(self._md.content.decode())
        ret.append(fp.name)
        self._book.logger.info('Download book: Created {}'.format(fp.name))

        self.item.get_file(self.item.identifier + '_meta.xml') \
            .download(file_path=self._book.path + '/metadata.xml')
        ret.append('{}'.format(self._book.path + '/metadata.xml'))
        self._book.logger.info('Download book: Created metadata.xml')
        self._book.reload_metadata()

        if not os.path.exists(os.path.join(self._book.path, 'reshooting')):
            os.makedirs(os.path.join(self._book.path, 'reshooting'))
            ret.append('{}'.format(self._book.path + '/reshooting'))
        self._book.logger.info('Download book: Created reshooting directory')

        self._files = ret

        self._book.logger.info('Download book: Created files, now converting '
                          'scandata from RePublisher XML to Scribe3 JSON')

    def _create_scandata(self):
        self.dispatch_progress('Creating scandata')
        sc_path = os.path.join(self._book.path, 'scandata.xml')

        tree = book_helpers.validate_scandata_xml(sc_path, self._book)
        scandata_xml = book_helpers.create_normalized_scandata(tree, self._book)
        json_data = book_helpers.convert_normalized_scandata_to_json(scandata_xml)

        json_new = {}

        self._book.logger.info('Download book: Now converting to Scribe3 JSON')
        json_new['bookData'] = book_helpers.build_bookdata(json_data, self._book)
        json_new['pageData'] = book_helpers.build_pagedata(json_data, self._book)

        with open(os.path.join(self._book.path, 'scandata.json'), 'w') as outfile:
            json.dump(json_new, outfile)
            self._book.logger.info('Download book: Created {}'.format(outfile.name))

        self._scandata= ScanData(self._book.path)
        self._scandata.save()

        self._book.reload_scandata()

        self._book.logger.info('Download book: Created scandata.')

    def _get_checkout_information(self):
        self.dispatch_progress('Pulling checkout information')
        book_checkout_url = ('https://{}/RePublisher/RePublisher-'
                             'checkoutBook.php?peek=true&id={}'
                             .format(self.item.d1, self._book.identifier))

        self._book.logger.info('Getting checkout information from {}'.format(book_checkout_url))
        ret = self._ia_session.get(book_checkout_url)
        self._book.logger.info('Got {} ({})'.format(ret.text, ret.status_code))
        self._checkout_info = json.loads(ret.text)

    def _write_claimer_file(self):
        self.dispatch_progress('Writing claimer file')
        if 'claimed_by' in self._checkout_info and self._checkout_info['claimed_by'] != False:
            claimer = self._checkout_info['claimed_by']
        else:
            claimer = '-'

        with open(os.path.join(self._book.path, 'claimer'), 'w+') as fp:
            fp.write(claimer)
        self._claimer = claimer
        self._book.logger.info('This book was claimed by {}'.format(claimer))

    def _download_proxies(self):
        self.dispatch_progress('Downloading proxies')
        all_ok = True
        counter = 0
        page_data = self._scandata.dump_raw()['pageData']
        for i, page in enumerate(page_data):
            self.dispatch_progress('Downloading proxies [{}/{}]'.format(i, len(page_data)))
            if int(page) != i:
                self._book.logger.error('Download book: Download Proxies: '
                             'CRITICAL MISMATCH')
                break
            short_msg = 'Download pics | {percent:.1f}% | {n}/{total}'.format(
                percent=i * 100 / len(page_data),
                n=i,
                total=len(page_data),
            )
            self._book.update_message(short_msg)
            url = book_helpers.get_cluster_proxy_url_by_leaf(self._scandata, self.item, page)
            res = self.download_proxy_image(page, self._book, url)

            all_ok = all_ok and res
            counter += 1
            if res:
                self._book.logger.debug('Download book: Got proxies for leaf #{0}'
                             .format(page))
            else:
                self._book.logger.error('Download book: Error downloading leaf #{0}'
                             .format(page))

            try:
                leafnr = self._scandata.get_page_num(page)['num']
            except Exception:
                pass

        self._book.logger.info('Download book: Downloaded {} proxy images.'
                    .format(counter))

        return all_ok

    def _set_states(self):
        self.dispatch_progress('Setting states')
        self._book.error = None
        if int(self.item.metadata['repub_state']) == 31:
            book_final_repub_state = 32
            self._download_type = 'corrections'
            self._book.do_end_download_correction()
        elif int(self.item.metadata['repub_state']) == 41:
            book_final_repub_state = 42
            self._download_type = 'foldouts'
            self._book.do_end_download_foldout()
        else:
            self._book.logger('Error while processing item in repub_state {}'.format(self.item.metadata['repub_state']))
            raise Exception('remote repub state in inconsistent with book download')

        self._book.logger.info('Setting remote repub_state to {}'.format(book_final_repub_state))
        mdapi_response = self.item.modify_metadata({'repub_state': book_final_repub_state})
        self._book.logger.info('Response from MDAPI: {}'.format(mdapi_response))
        if mdapi_response:
            self._mdapi_response_text = mdapi_response.text
            self._book.logger.info('Body of MDAPI: {}'.format(self._mdapi_response_text))
            if mdapi_response.status_code != 200:
                raise Exception('MDAPI response was not OK! - Got this instead: {} - {}'.format(
                    mdapi_response.status_code, mdapi_response.text
                ))

            self._book.logger.info('Download book: Set book repub_state to {}'.format(book_final_repub_state))
            self._book_final_repub_state = book_final_repub_state
        else:
            raise Exception('No response from MDAPI. Aborting download.')

    def _send_stats(self):
        self.dispatch_progress('Notifying iabdash')
        payload = {
            'repub_state': self._book_final_repub_state,
            'checkout_info': self._checkout_info,
            'claimer': self._claimer,
            'files': self._files,
        }
        push_event('tts-book-downloaded', payload, 'book', self.identifier, os.path.join(self._book.path, "iabdash.log"))
        self.notifications_manager.add_notification(title='Downloaded',
                                                    message="{} has been downloaded and is ready for {}.".format(self.identifier, self._download_type),
                                                    show_system_tile=False,
                                                    book=self._book)

    def _release_lock(self):
        total_time = 100
        self._book.logger.info('Download book: ------ DONE. Downloaded {0} in '
                    '{1}s ----------'.format(self.identifier, total_time))
        self._book.release_lock()

    def download_proxy_image(self, page, book, url,):

        def is_proxy_valid(proxy_path):
            return True

        file_target = '{n:04d}.jpg'.format(n=int(page))
        dest = os.path.os.path.join(book.path, "thumbnails", file_target)

        if url is not None:
            image = self._ia_session.get(url).content
            with open(dest, 'wb+') as proxy:
                book.logger.debug('Writing {}'.format(dest))
                proxy.write(image)
                book.logger.info('Download book: Written {}'.format(proxy.name))
        else:
            import shutil
            book.logger.debug('Page {} has no proxy, adding missing '
                         'image at {}'.format(page, dest))
            shutil.copyfile(scribe_globals.MISSING_IMAGE, dest)
        ret = is_proxy_valid(dest)
        return ret

class SyncDownloadsTask(MetaSchedulerTask):

    def __init__(self, **kwargs):
        self._library = kwargs.pop('library')
        super(SyncDownloadsTask, self).__init__(**kwargs)
        self._priority = 'medium'

        self._download_list = []

    def _prepare(self):
        super(SyncDownloadsTask, self)._prepare()
        del self._download_list[:]
        identifiers_to_be_downloaded = btserver.get_corrections_list(self.logger)
        if not identifiers_to_be_downloaded:
            return []

        for identifier in identifiers_to_be_downloaded:
            other_books_with_same_identifier = self._library.get_books('identifier', identifier)
            if other_books_with_same_identifier:
                skip = False
                for book_on_disk in other_books_with_same_identifier:
                    if 'corrections' in book_on_disk.status \
                        or 'foldouts' in book_on_disk.status \
                        or book_on_disk.status == 'download_incomplete':
                            skip = True
                            self.logger.info('Books Download: Skipping {}.'.format(book_on_disk))
                if skip:
                    continue
            self.logger.info('Books Download: Pending Downloads: Adding {0} '
                         'to download pool.'.format(identifier))
            self._download_list.append(identifier)

    def _fill_list(self):
        self.logger.info('Download books: Got {} books to download'
                    .format(len(self._download_list)))

        for book in self._download_list:
            task = DownloadBookTask(library=self._library,
                                    identifier=book)
            self._tasks_list.append(task)
