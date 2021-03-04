from m2r import parse_from_file

from ia_scribe.tasks.generic import CallbackTask


class LoadHelpDocumentsTask(CallbackTask):

    def __init__(self, to_load, **kwargs):
        self.to_load = to_load
        self.result = {}
        super(LoadHelpDocumentsTask, self).__init__(**kwargs)

    def create_pipeline(self):
        return [
            self._load,
            self._do_call_back
        ]

    def _load(self):
        for entry in self.to_load:
            res = parse_from_file(entry['file'])
            self.result[entry['key']] = res
