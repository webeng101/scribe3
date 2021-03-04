import os
from enum import Enum
from ia_scribe.abstract import singleton, Observable
from ia_scribe.tasks.update import CheckUpdateStatusTask, DoUpdateTask, RunDaemonTask, UpdateDaemonTask, UpdatePPATask
from ia_scribe.notifications.notifications_manager import NotificationManager
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe import scribe_globals

notifications_manager = NotificationManager()
config = Scribe3Configuration()

SCRIBE3_PPA = '/etc/apt/sources.list.d/ia-scribe.list'
ALLOWED_TARGETS = ['scribe-repo-autobuild-dev',
                   'scribe-repo-autobuild-alpha',
                   'scribe-repo-autobuild-beta',
                   'scribe-repo-autobuild-internal', ]

class UpdateStatus(Enum):
    up_to_date = 100
    update_available = 200
    updating = 300
    updated = 400
    error = 800
    unknown = 900

UpdateStatus_HR = {
    'up_to_date': 'You are running the latest version.',
    'update_available': 'An update is available. Click on the button to download it and install it.',
    'updating': 'An update is being installed.',
    'updated': 'An update was installed. Restart to enable it.',
    'error': 'Update error',
    'unknown': 'Unknown package status. You may be running from code.',
}

@singleton
class UpdateManager(Observable):

    update_status = UpdateStatus.unknown
    update_version = None
    current_version = None
    error = None
    task_scheduler = None
    update_channel = None
    observers = set([])

    def load_channel(self):
        try:
            ppa = ''
            with open(SCRIBE3_PPA, 'r') as file:
                ppa = file.read()
            ppa_parsed = ppa.split('/')[-2].rstrip()
            self.update_channel = ppa_parsed
            self.notify('update_channel_changed')
        except Exception:
            self.update_channel = 'None configured or could not read'

    def get_update_channel(self):
        return self.update_channel

    def set_update_channel(self, target):
        if target not in ALLOWED_TARGETS:
            return False
        concrete_task = UpdatePPATask(target=target,
                                      PPA_FILE=SCRIBE3_PPA,
                                      callback=self._set_update_channel_callback)
        self.task_scheduler.schedule(concrete_task)

    def _set_update_channel_callback(self, task):
        self.update_channel = task.result
        self.notify('update_channel_changed')

    def run_daemon(self):
        concrete_task = RunDaemonTask()
        self.task_scheduler.schedule(concrete_task)

    def update_daemon(self):
        concrete_task = UpdateDaemonTask()
        self.task_scheduler.schedule(concrete_task)

    def get_update_status(self, human_readable=False):
        """
        Part of the external API, this function is authoritative to return
        the update status.

        :param human_readable:
        :return:
        """
        ret = self.update_status.name
        if human_readable:
            ret = UpdateStatus_HR[self.update_status.name]
        return ret

    def get_build_tag(self):
        return scribe_globals.BUILD_NUMBER

    def schedule_update_check(self):
        """
        This is called when the screen is initialized by ScribeWidget, and
        schedules the update task to be (potentially) periodic if the users
        turned on the option in settings
        """
        update_interval = config.get_numeric_or_none('check_for_update_interval')
        if update_interval:
            self.do_check_update(
                periodic=True,
                interval=update_interval * 3600 # hours
            )

    def do_check_update(self, periodic=None, interval=None, task_handler_class=None):
        """
        This actually schedules the update task. Used by the button too.

        :param periodic:
        :param interval:
        :param task_handler_class:
        :return:
        """
        self.load_channel()
        if task_handler_class:
            task_arguments = {'task_type': CheckUpdateStatusTask,
                              'callback': self._do_check_update_callback,}
            if periodic:
                task_arguments['periodic'] = periodic
                task_arguments['interval'] = interval
            concrete_handler = task_handler_class(**task_arguments)
            concrete_task = concrete_handler.task
        else:
            concrete_task = CheckUpdateStatusTask(callback=self._do_check_update_callback,
                                                  periodic=periodic,
                                                  interval=interval)
        self.task_scheduler.schedule(concrete_task)

    def _do_check_update_callback(self, task):
        if not task.result:
            self.error = task
            self.notify('error')
            return

        self.current_version = task.installed
        self.update_version = task.candidate

        if self.current_version == self.update_version:
            self.update_status = UpdateStatus.up_to_date
        elif self.current_version != self.update_version:
            self.update_status = UpdateStatus.update_available
            self._update_available_found()
        self.notify('update_status_refreshed')

    def _update_available_found(self):
        if config.is_true('auto_update'):
            notifications_manager.add_notification(
                title='Installing update',
                message='Scribe3 version {} is now available. '
                        'As auto-updates are on, it will be installed in the background.'.format(self.update_version),
                notification_type='system',
            )
            self.do_update()
        else:
            notifications_manager.add_notification(
                title='Update available',
                message='Scribe3 version {} is now available. '
                        'Visit Options -> Update to install it.'.format(self.update_version),
                notification_type='system',
                show_system_tile=True,
            )

    def do_update(self, task_handler_class=None):
        if task_handler_class:
            concrete_handler = task_handler_class(
                task_type=DoUpdateTask,
                callback=self._do_update_callback,
            )
            concrete_task = concrete_handler.task
        else:
            concrete_task = DoUpdateTask(callback=self._do_update_callback)
        self.task_scheduler.schedule(concrete_task)
        self.update_status = UpdateStatus.updating
        self.notify('update_status_refreshed')
        return True

    def _do_update_callback(self, task):
        self.update_status = UpdateStatus.updated
        notifications_manager.add_notification(
            title='Update installed',
            message='Scribe3 version {} was installed.\n'
                    'Restart the app to enable it.'.format(self.update_version),
            show_system_tile=True,
        )
        self.update_status = UpdateStatus.updated
        self.notify('update_status_refreshed')

