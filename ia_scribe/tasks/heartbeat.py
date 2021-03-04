from pprint import pformat

from ia_scribe.breadcrumbs import other_stats
from ia_scribe import utils, scribe_globals
from ia_scribe.book.metadata import get_metadata
from ia_scribe.tasks.task_base import TaskBase
from ia_scribe.ia_services.iabdash import push_event
from ia_scribe.cameras.optics import Cameras

class HeartbeatTask(TaskBase):

    def __init__(self, **kwargs):
        self._library = kwargs.pop('library')
        super(HeartbeatTask, self).__init__(**kwargs)
        self._payload = {}

    def create_pipeline(self):
        return [
            self._get_version,
            self._get_disk_stats,
            self._get_dir_stats,
            self._get_uptime_state,
            self._get_temperature_stats,
            self._get_cpu_stats,
            self._get_camera_stats,
            self._get_library_stats,
            self._get_scribe_app_settings,
            self._get_scribe_app_metadata,
            self._upload_payload
        ]

    def _get_version(self):
        self.dispatch_progress('Getting software version')
        self._payload['tts_version'] = scribe_globals.BUILD_NUMBER

    def _get_disk_stats(self):
        self.dispatch_progress('Getting disk stats')
        self._payload['disk_stats'] = other_stats.get_fs_stats()

    def _get_dir_stats(self):
        self.dispatch_progress('Getting directory stats')
        self._payload['directory_stats'] = other_stats.get_dir_stats()

    def _get_uptime_state(self):
        self.dispatch_progress('Getting uptime stats')
        self._payload['uptime'] = other_stats.get_uptime_stats()

    def _get_temperature_stats(self):
        self.dispatch_progress('Getting temperature stats')
        self._payload['temperature_stats'] = other_stats.get_temperature_stats()

    def _get_cpu_stats(self):
        self.dispatch_progress('Getting CPU stats')
        self._payload['cpu_stats'] = other_stats.get_cpu_stats()

    def _get_camera_stats(self):
        self.dispatch_progress('Getting camera stats')
        cameras = Cameras()
        active_cameras = cameras.get_active_cameras()
        self._payload['camera_config'] = active_cameras

    def _get_library_stats(self):
        self.dispatch_progress('Getting library stats')
        try:
            lib_stats = self._library.get_stats()
            self._payload['bookslist_stats'] = lib_stats
        except Exception:
            self.logger.exception('Unable to get library stats. Skipping...')

    def _get_scribe_app_metadata(self):
        self.dispatch_progress('Getting Scribe app metadata')
        metadata = get_metadata(scribe_globals.CONFIG_DIR)
        local_metadata = \
            dict((k, v) for k, v in metadata.items() if v)
        self._payload['local_metadata'] = local_metadata

    def _get_scribe_app_settings(self):
        self.dispatch_progress('Gathering local settings')
        self._payload['local_settings'] = utils.get_local_settings()

    def _upload_payload(self):
        self.dispatch_progress('Uploading')
        push_event('tts-heartbeat', self._payload.copy())
        self.logger.debug('{}: Payload:\n{}'
                         .format(self.name, pformat(self._payload)))
