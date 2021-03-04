import re, subprocess

from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.notifications.notifications_manager import NotificationManager
from ia_scribe.tasks.generic import SubprocessTask, CallbackTask

nm = NotificationManager()
config = Scribe3Configuration()

PACKAGE_NAME = 'ia-scribe'

class UpdateAptSourcesTask(SubprocessTask):

    def __init__(self, **kwargs):
        kwargs['command'] = 'sudo apt-get update'
        super(UpdateAptSourcesTask, self).__init__(**kwargs)


class RunUpdateCommandTask(SubprocessTask):

    def __init__(self, package_name, **kwargs):
        kwargs['command'] = 'sudo apt-get install {} --reinstall -y'.format(package_name)
        super(RunUpdateCommandTask, self).__init__(**kwargs)


class AptPolicyTask(SubprocessTask):

    def __init__(self, package_name, **kwargs):
        kwargs['command'] = 'sudo apt-cache policy {}'.format(package_name)
        super(AptPolicyTask, self).__init__(**kwargs)


class RunDaemonTask(SubprocessTask):

    def __init__(self, **kwargs):
        kwargs['command'] = 'sudo ~/scribe-daemon/dispatch.sh'
        super(RunDaemonTask, self).__init__(**kwargs)


class UpdateDaemonTask(SubprocessTask):

    def __init__(self, **kwargs):
        kwargs['command'] = 'sudo sh ~/scribe-daemon/update.sh'
        super(UpdateDaemonTask, self).__init__(**kwargs)


class UpdatePPATask(CallbackTask):
    def __init__(self, target, PPA_FILE, **kwargs):
        self._target = target
        self._PPA_FILE = PPA_FILE
        self.result = None
        super(UpdatePPATask, self).__init__(**kwargs)

    def create_pipeline(self):
        return [
            SubprocessTask(command='''sudo bash -c "echo 'deb [trusted=yes] https://archive.org/download/{target} /' > {target_file}"'''.format(
                                    target=self._target,
                                    target_file=self._PPA_FILE),
                                    callback=self._parse_result,
                            ),
            UpdateAptSourcesTask(),
            self._do_call_back
        ]

    def _parse_result(self, status_code, output, error, *args):
        if error:
            raise Exception(error)
        self.result = self._target


class CheckUpdateStatusTask(CallbackTask):

    def __init__(self, **kwargs):
        self._package_name = PACKAGE_NAME
        self._update_status = None
        self.result = None
        super(CheckUpdateStatusTask, self).__init__(**kwargs)

    def create_pipeline(self):
        return [
            UpdateAptSourcesTask(),
            AptPolicyTask(package_name=self._package_name,
                          callback=self._parse_result),
            self._do_call_back
            ]

    def _parse_result(self, status_code, output, error, *args):
        self.result = output
        if error or output in [None, '']:
            self.error = error
            return

        tags = re.findall('Candidate:.*|Installed:.*', output)
        self.installed = tags[0].split('Installed: ')[1]
        self.candidate = tags[1].split('Candidate: ')[1]


class DoUpdateTask(CallbackTask):

    def __init__(self, **kwargs):
        self._package_name = PACKAGE_NAME
        self._update_status = None
        self.result = None
        super(DoUpdateTask, self).__init__(**kwargs)

    def create_pipeline(self):
        return [
            UpdateAptSourcesTask(),
            RunUpdateCommandTask(
                package_name=self._package_name,
                callback=self._parse_result),
            self._do_call_back
        ]

    def _parse_result(self, exit_code, output, error, *args):
        self.output = output
        self.exit_code = exit_code
        if self.exit_code == 0:
            self.result = True
        else:
            self.error = RuntimeError(error)





