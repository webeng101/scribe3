import internetarchive

from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.tasks.task_base import TaskBase

config = Scribe3Configuration()


class IALoginTask(TaskBase):
    error = None
    result = None

    def __init__(self, **kwargs):
        self.email = kwargs.pop('email')
        self.password = kwargs.pop('password')
        self.callback = kwargs.pop('callback')
        super(IALoginTask, self).__init__(**kwargs)

    def create_pipeline(self):
        return [self._login,
                self._callback,
                ]

    def _login(self):
        self.dispatch_progress('Logging in with IA...')
        try:
            self.result = internetarchive.config.get_auth_config(self.email, self.password)
        except Exception as e:
            self.error = e

    def _callback(self):
        self.callback(self.result, self.error)


