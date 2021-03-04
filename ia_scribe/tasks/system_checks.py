from ia_scribe import scribe_globals
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.notifications.notifications_manager import NotificationManager
from ia_scribe.tasks.task_base import TaskBase
from ia_scribe.tasks.generic import SubprocessTask
from ia_scribe.tasks.meta import LinearSchedulerTask


nm = NotificationManager()
config = Scribe3Configuration()


class SystemChecksTask(TaskBase):

    def __init__(self, **kwargs):
        super(SystemChecksTask, self).__init__(**kwargs)

    def create_pipeline(self):
        return [

            #self._check_cookie,
            self._check_exiftool,
            ]

    def _check_cookie(self):
        if False:
            message = "The scribe's archive.org cookie has expired. Uploads will not be possible " \
                      "until it has been refreshed. Notify your Manager or an Admin to resolve the issue."

            nm.add_notification(
                title='System cookie expired',
                message=message,
                is_sticky=True,
                notification_type='system',
            )

    def _check_exiftool(self):
        if not (scribe_globals.EXIFTOOL):
            message = 'EXIF tags won\'t be copied. Install Exiftool on your system to disable this alert.'
            nm.add_notification(
                title='Exiftool not found',
                message=message,
                is_sticky=True,
                notification_type='system',
            )


class NetworkCheckTask(LinearSchedulerTask):

    NETWORK_TEST_COMMANDS = [
        'ip addr',
        'ping 8.8.8.8 -c 5',
        'dig archive.org',
        'ping archive.org -c 5',
        'traceroute archive.org',
        'curl ipinfo.io',
        'curl http://s3.us.archive.org/?check_limit=1'
    ]
    results = []

    def __init__(self, **kwargs):
        self._increment_callback = kwargs.get('increment_callback')
        super(NetworkCheckTask, self).__init__(**kwargs)
        self._priority = 'medium'

    def _build_pipeline_steps(self):
        pipeline = []
        for command in self.NETWORK_TEST_COMMANDS:
            task = SubprocessTask(command=command,
                                  callback=self._incremental_callback)
            pipeline.append(task)
        return pipeline

    def _incremental_callback(self, exit_code, output, error, task):
        self.dispatch_progress('Received result from {}'.format(task._command))
        if self._increment_callback:
            self._increment_callback(exit_code, output, error, task)
        else:
            self.results.append((task._command, output, error))
