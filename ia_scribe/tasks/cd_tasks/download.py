import os
import time
from uuid import uuid4

from ia_scribe.book.scandata import ScanData
from ia_scribe.ia_services.btserver import get_ia_session
from ia_scribe.ia_services.iabdash import push_event
from ia_scribe.notifications.notifications_manager import NotificationManager
from ia_scribe.tasks.task_base import TaskBase, CANCELLED_WITH_ERROR


class DownloadCDTask(TaskBase):

    def __init__(self, **kwargs):
        super(DownloadCDTask, self).__init__(**kwargs)
        self._cd = None
        self._priority = 'medium'
        self._library = kwargs['library']
        self.identifier = kwargs['identifier']
        self.logger.info('Download CD: Downloading {}'.format(self.identifier))
        self.notifications_manager = NotificationManager()
        self._download_type = None
        self.start_time = None
        self.total_time = None


    def create_pipeline(self):
        return [
            self._begin,
            self._get_ia_session,
            self._load_item,
            self._verify_is_CD,
            self._verify_is_stub_item,
            self._create_stub_CD,
            self._create_files,
            self._create_scandata,
            self._set_states,
            self._release_lock,
            self._send_stats,
        ]

    def _begin(self):
        self.start_time = time.time()

    def handle_event(self, event_name, *args, **kwargs):
        if event_name == 'on_state' and self.state == CANCELLED_WITH_ERROR:
            if self._cd:
                self._cd.do_move_to_trash()
                self._cd.do_delete_anyway()

    def _get_ia_session(self):
        self.dispatch_progress('Getting IA session')
        self._ia_session = get_ia_session()

    def _load_item(self):
        self.dispatch_progress('Loading item')
        self.item = self._ia_session.get_item(self.identifier)
        self.logger.info('Download CD: target item: {}'
                    .format(self.item.identifier))

    def _verify_is_CD(self):
        self.dispatch_progress('Verifying this is an ArchiveCD item')
        mediatype = self.item.metadata.get('mediatype')
        software_version = self.item.metadata.get('software_version')
        assert mediatype == 'audio', 'This is not an audio item. It is {}.'.format(mediatype)
        assert software_version is not None, 'This item was not created with ArchiveCD'
        assert 'ArchiveCD' in software_version, 'This item was not created with ArchiveCD'

    def _verify_is_stub_item(self):
        self.dispatch_progress('Verifying this is a stub item')
        stub_file = self.item.get_file('stub.txt')
        #if not stub_file.exists:
        #    raise Exception('No stub file found!')

    def _create_stub_CD(self):
        self.dispatch_progress('Creating local CD')
        message = "This CD is being downloaded and no actions are available just yet."
        cd_id = str(uuid4())
        self._cd = self._library.new_cd(cd_id, status='download_incomplete', error=message)
        self._cd.set_lock()
        self._cd.logger.info('Download CD: Created stub CD {}'.format(self._cd))

    def _create_files(self):
        self.dispatch_progress('Downloading files')
        ret = []
        with open(os.path.join(self._cd.path, 'identifier.txt'), 'w+') as fp:
            fp.write(self.item.identifier)
        ret.append(fp.name)
        self._cd.logger.info('Download CD: Created {}'.format(fp.name))

        with open(os.path.join(self._cd.path, 'downloaded'), 'w+') as fp:
            fp.write('True')
            ret.append(fp.name)
        self._cd.logger.info('Download CD: Created {}'.format(fp.name))

        with open(os.path.join(self._cd.path, 'uuid'), 'w+') as fp:
            fp.write(self._cd.uuid)
        ret.append(fp.name)
        self._cd.logger.info('Download CD: Created {}'.format(fp.name))

        self.item.get_file(self.item.identifier + '_meta.xml') \
            .download(file_path=self._cd.path + '/metadata.xml')
        ret.append('{}'.format(self._cd.path + '/metadata.xml'))
        self._cd.logger.info('Download CD: Created metadata.xml')
        self._cd.reload_metadata()

        if not os.path.exists(os.path.join(self._cd.path, 'thumbs')):
            os.makedirs(os.path.join(self._cd.path, 'thumbs'))
            ret.append('{}'.format(self._cd.path + '/thumbs'))
        self._cd.logger.info('Download CD: Created thumbs directory')

        self.item.get_file(self.item.identifier + '_itemimage.png') \
            .download(file_path=self._cd.path + '/cover.png')
        ret.append('{}'.format(self._cd.path + '/cover.png'))
        self._cd.logger.info('Download CD: Downloaded cover')

        self._files = ret

        self._cd.logger.info('Download CD: Created files.')

    def _create_scandata(self):
        self.dispatch_progress('Creating scandata')

        self._scandata=\
            ScanData(self._cd.path)
        self._scandata.save()
        self._cd.reload_scandata()

        self._cd.logger.info('Download CD: Created scandata.')


    def _set_states(self):
        self.dispatch_progress('Setting states')
        self._cd.do_finish_download()

    def _send_stats(self):
        self.dispatch_progress('Notifying iabdash')
        payload = {
            'files': self._files,
            'total_time': self.total_time,
        }
        push_event('tts-cd-downloaded', payload, 'cd', self.identifier, os.path.join(self._cd.path, "iabdash.log"))

        self.notifications_manager.add_notification(title='Downloaded',
                                                    message="CD {} has been downloaded.".format(self.identifier),
                                                    show_system_tile=False,
                                                    book=self._cd)

    def _release_lock(self):
        self.total_time = time.time() - self.start_time
        self._cd.logger.info('Download CD: ------ DONE. Downloaded {0} in '
                    '{1}s ----------'.format(self.identifier, self.total_time))
        self._cd.release_lock()
