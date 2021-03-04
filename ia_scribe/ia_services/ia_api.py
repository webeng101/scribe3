"""
ia_api tools

a library wrapping the Internet Archive API

:copyright: (c) 2016 Internet Archive.
:author: Giovanni Damiola <gio@archive.org>
:license: AGPL 3, see LICENSE for more details.
"""

import logging
from io import StringIO
import datetime
import sys
import internetarchive as ia
from ia_scribe import scribe_globals
from ia_scribe.ia_services.btserver import get_ia_session

# initializing logger
log = logging.getLogger('BTSERVER')
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter=logging.Formatter(scribe_globals.LOGGING_FORMAT)
handler.setFormatter(formatter)
log.addHandler(handler)

'''
import raven, traceback
from raven import *
from raven.conf import setup_logging
from raven.handlers.logging import SentryHandler

raven_client = Client(dsn="https://4af7fdad024f412eb45b933a400344a4"
                          ":6434bde2c4da4f2ab6ea3a658043bb96"
                          "@books-sentry.us.archive.org/3",
                        release = smeta['tts_version'], 
                        data= {
                                'scanner' : smeta['scanner'],
                                'language' : smeta['language'],
                                'contributor' : smeta['contributor'],
                                'sponsor' : smeta['sponsor'],
                                'operator' : smeta['operator'],
                            }
                        )

sentry_handler = SentryHandler(raven_client)
log.addHandler(sentry_handler)
sentry_errors_log = logging.getLogger("sentry.errors")
sentry_errors_log.addHandler(logging.StreamHandler())
'''


class InternetArchive():
    """Class to use the Internet Archive
    """
    DEFAULT_COLLECTION = 'iabooks-btserver'
    DEFAULT_FILENAME = 'info.json'
    DEFAULT_CONTENT_VALUE = 'nothing here'

    def __init__(self, metadata, **kwargs):
        #super(InternetArchive, self).__init__(**kwargs)
        self.SCRIBE_METADATA = metadata

        self.s = get_ia_session()
        self.SECURE = self.s.secure
        log.info("Initialized InternetArchive object")
        # Check that user has btserver privs

    def add_file_item(self,
                identifier, 
                collection = None, 
                filename=None, 
                content=None): 

        if collection is None:
            collection = self.DEFAULT_COLLECTION

        if filename is None:
            filename = self.DEFAULT_FILENAME

        if content is None:
            content = self.DEFAULT_CONTENT_VALUE

        log.info("Creating item {0} in collection {1}, with {2} = '{3}'".format(identifier, collection, filename, content))
        file_handler = StringIO(content)
        file_handler.name = filename
        item = self.s.get_item(identifier)
        res = item.upload(file_handler, metadata={'collection': collection, 'mediatype': 'texts'})
        if res[0].status_code != 200:
            log.error("Response code: {0} - cannot create the item {1}".format(res[0].status_code,identifier))
            return res
        else:
            log.info("Item {0} created with success.".format(identifier))
            return res

    def del_file_item(self, identifier,filename):
        item = self.s.get_item(identifier)
        res = item.delete(filename)
        return res

    def show_all(self, collection=None):
        collection = self.DEFAULT_COLLECTION
        search = ia.search_items('collection:'+collection)
        data = []
        for i in search:
            data.append(i)
        return data

    def get_item_metadata(self, identifier):
        item = self.s.get_item(identifier)
        return(item.metadata)

    def get_item_file(self, identifier,filename):
        item = self.s.get_item(identifier)
        ff = item.get_file(filename)
        r = item.session.get(ff.url)
        return r.content
        
    def set_item_metadata(self, identifier,metadata):
        if self.item_exists(identifier):
            log.info("{0}: updating metadata with: {1}".format(identifier,metadata))
            item = self.s.get_item(identifier)
            #dict_metadata = ast.literal_eval(metadata)
            dict_metadata = metadata
            dict_metadata['last_update'] = str(datetime.datetime.now())[:-7]
            res = item.modify_metadata(dict_metadata)
            return res.status_code
        else:
            log.error("Cannot update metadata for {0}: Item does not exist".format(identifier))
            return False

    def item_exists(self, identifier):
        item = self.s.get_item(identifier)
        if item.exists:
            return True
        else:
            return False
