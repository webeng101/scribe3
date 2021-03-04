import json

import requests

from ia_scribe.tasks.generic import CallbackTask


class RCSSyncTask(CallbackTask):

    def __init__(self, **kwargs):
        self._url = kwargs['url']
        super(RCSSyncTask, self).__init__(**kwargs)

    def create_pipeline(self):
        return [
            self._call_remote,
            self._validate_response,
            self._load_data,
            self._validate_data,
            self._do_call_back,
            ]

    def _call_remote(self):
        self._response = requests.get(self._url)

    def _load_data(self):
        self._data = json.loads(self._response.text)

    def _validate_response(self):
        if self._response.status_code != 200:
            raise Exception('Response {} received from server'.
                            format(self._response.status_code))
        if len(self._response.text) == 0:
            raise Exception('Received zero-length response from server')

    def _validate_data(self):
        pass
