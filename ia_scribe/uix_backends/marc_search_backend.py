import json

import requests
from kivy.properties import ObjectProperty, DictProperty, StringProperty

from ia_scribe.scribe_globals import ZFETCH_URL
from ia_scribe.uix_backends.widget_backend import WidgetBackend


class MARCSearchBackend(WidgetBackend):
    query = StringProperty(allownone=True)
    results = ObjectProperty(allownone=True)
    error = ObjectProperty(allownone=True)
    concrete_url = StringProperty(allownone=True)


    EVENT_SEARCH_FAILURE = 'on_search_failure'
    EVENT_SEARCH_RESULTS = 'on_search_results'

    __events__ = (EVENT_SEARCH_FAILURE, EVENT_SEARCH_RESULTS)

    def __init__(self, **kwargs):
        super(MARCSearchBackend, self).__init__(**kwargs)

    def init(self):
        if not self.is_initialized():
            super(MARCSearchBackend, self).init()

    def reset(self):
        if self.is_initialized():
            super(MARCSearchBackend, self).reset()

    def thread_search(self, url, callback):
        print(url)
        res = requests.get(url)
        callback(res)

    def search(self, *args, **kwargs):
        query_list = ['{key}={value}'.format(key=entry['key'], value=entry['value'])
                      for entry in kwargs['form_data']]
        self.query = ' and '.join(query_list)
        self.concrete_url = ZFETCH_URL.format(catalog=kwargs['catalog'], query=self.query)
        self.search_internal()

    def search_internal(self):
        from threading import Thread
        t = Thread(target=self.thread_search,
                 args=(self.concrete_url, self.search_callback),
                 name='RequestsThread')
        t.start()

    def go_next(self):
        next_result = self.results['query'].get('next')
        if next_result:
            self.concrete_url = next_result
            self.search_internal()
        return next_result

    def go_previous(self):
        prev_result = self.results['query'].get('prev')
        if prev_result:
            self.concrete_url = prev_result
            self.search_internal()
        return prev_result

    def search_callback(self, res):
        if res.status_code != 200:
            self.error = json.loads(res.text)
            self.results = None
            self.dispatch(self.EVENT_SEARCH_FAILURE)
            return
        else:
            try:
                self.results = json.loads(res.text)
                self.error = None
                self.dispatch(self.EVENT_SEARCH_RESULTS)
                return
            except Exception as e:
                self.error = e
                self.results = None
                self.dispatch(self.EVENT_SEARCH_FAILURE)
                return

    def on_search_failure(self, *args):
        pass

    def on_search_results(self, *args):
        pass

    def on_error(self, *args):
        pass

    def on_results(self, *args):
        pass

    def on_query(self, *args):
        pass

    def on_concrete_url(self, *args):
        pass
