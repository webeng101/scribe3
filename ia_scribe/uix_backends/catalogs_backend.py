import os, json
from kivy.properties import DictProperty
import json
import os

import requests
from kivy.properties import DictProperty

from ia_scribe.scribe_globals import ZTARGETS_URL, ZTARGETS_FULL_PATH
from ia_scribe.uix_backends.widget_backend import WidgetBackend

'''
Responsibilities: 

- Interact with ztargets to maintain a list of catalogs and support on-demand update
- Maintain a notion of recently used catalogs
- Provide fast access to ztargets list
- Have a notion of default catalog
'''


class CatalogsBackend(WidgetBackend):

    catalogs = DictProperty()

    EVENT_CATALOGS_LOADED = 'on_catalogs_loaded'
    EVENT_CATALOGS_LOADING_ERROR = 'on_catalogs_loading_error'
    EVENT_CATALOGS_CHANGED = 'on_catalogs_changed'
    EVENT_DEFAULT_CATALOG_SET = 'on_default_catalog_set'

    __events__ = (EVENT_CATALOGS_LOADED, EVENT_DEFAULT_CATALOG_SET,
                  EVENT_CATALOGS_LOADING_ERROR, EVENT_CATALOGS_CHANGED)

    def __init__(self, **kwargs):
        super(CatalogsBackend, self).__init__(**kwargs)

    def init(self):
        if not self.is_initialized():
            super(CatalogsBackend, self).init()
            self.load_catalogs()

    def reset(self):
        if self.is_initialized():
            super(CatalogsBackend, self).reset()
            self.catalogs = []

    def download_catalogs(self, overwrite=False):
        if os.path.exists(ZTARGETS_FULL_PATH):
            if os.stat(ZTARGETS_FULL_PATH).st_size != 0:
                if not overwrite:
                    return ZTARGETS_FULL_PATH
        r = requests.get(ZTARGETS_URL, allow_redirects=True)
        open(ZTARGETS_FULL_PATH, 'w+').write(r.text)
        return ZTARGETS_FULL_PATH

    def parse(self, file_path):
        with open(file_path, 'r') as file:
            ret = json.loads(file.read())
        return ret

    def load_catalogs(self):
        catalogs_file = self.download_catalogs()
        if catalogs_file:
            self.catalogs = self.parse(catalogs_file)
            self.dispatch(self.EVENT_CATALOGS_LOADED)
        else:
            self.dispatch(self.EVENT_CATALOGS_LOADING_ERROR)

    def on_catalogs(self, *args):
        self.dispatch(self.EVENT_CATALOGS_CHANGED)

    def on_catalogs_loaded(self, *args):
        pass

    def on_catalogs_loading_error(self, *args):
        pass

    def on_catalogs_changed(self, *args):
        pass

    def on_default_catalog_set(self, *args):
        pass

    def get_catalogs_list(self):
        ret = list(self.catalogs.keys())
        return ret

    def get_fields(self, catalog_name):
        raw_ret = self.catalogs.get(catalog_name)
        ret = list(raw_ret.values())
        return ret

    def filter(self, text):
        if text == '':
            filtered_catalogs = self.catalogs
        else:
            filtered_catalogs = [x for x in self.catalogs if text.lower() in x.lower()]
        return filtered_catalogs
