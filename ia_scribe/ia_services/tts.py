"""
tts tools

a library to operate on btserver items

"""

import logging
import sys
import socket
from pprint import pformat

import rstr

from ia_scribe.ia_services.ia_api import InternetArchive
from ia_scribe.scribe_globals import BUILD_NUMBER, LOGGING_FORMAT
from ia_scribe.book.metadata import get_metadata
from ia_scribe import scribe_globals
from ia_scribe.config.config import Scribe3Configuration

log = logging.getLogger('TTSServices')
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter=logging.Formatter(LOGGING_FORMAT)
handler.setFormatter(formatter)
log.addHandler(handler)

from raven import *
from raven.handlers.logging import SentryHandler
config = Scribe3Configuration()

def get_scanner_name():
    raw_md = get_metadata(scribe_globals.CONFIG_DIR)
    metadata = dict((k, v) for k, v in raw_md.items() if v)
    ret = metadata.get('scanner')
    return ret if ret else socket.gethostname()

raven_client = Client(
    dsn='https://4af7fdad024f412eb45b933a400344a4'
        ':6434bde2c4da4f2ab6ea3a658043bb96@books-sentry.us.archive.org/3',
    release=BUILD_NUMBER,
    name=get_scanner_name()
)
sentry_handler = SentryHandler(raven_client)
log.addHandler(sentry_handler)



def dict_compare(d1, d2):
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    intersect_keys = d1_keys.intersection(d2_keys)
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    modified = {o : (d1[o], d2[o]) for o in intersect_keys if d1[o] != d2[o]}
    same = set(o for o in intersect_keys if d1[o] == d2[o])
    return added, removed, modified, same


class TTSServices(InternetArchive):
    def __init__(self, metadata, **kwargs):
        InternetArchive.__init__(self, metadata, **kwargs)
        self.REGEX_IDENTIFIER = 'tts[A-Z]{2}[0-9]{4}'

    def show_all_tts(self):
        tts_data = self.show_all()
        data = []
        for i in tts_data:
            data.append(i['identifier'])
        return data


    def is_metadata_updated(self, tts_id, local_metadata):
        remote_metadata = self.get_item_metadata(tts_id)
        #print "remote metadata:", remote_metadata        
        if 'books' not in remote_metadata.keys():
            #print "books not in remote metadata, adding..."
            local_metadata['books'] = '[]'
        added, removed, modified, same = dict_compare(local_metadata, remote_metadata)
        log.info(
            "Scanner: {3}\nAdded:\n{0}\nRemoved:\n{1}\nModified:\n{2}"
            .format(
                pformat(added) if added else '{}',
                pformat(removed) if removed else '{}',
                pformat(modified) if modified else '{}',
                tts_id
            )
        )
        if added or modified:
            return False
        else:
            return True

    def register_tts(self, tts_id= None, metadata='{}'):
        if not tts_id:
            tts_id = self._generate_id_for_tts()
            self.register_tts(tts_id, metadata)
        else:
            if self._validate_id(tts_id):
                if self._create_tts_item(tts_id):
                    #time.sleep(4)
                    if self.update_metadata_tts(tts_id,metadata):
                        msg = "New Scribe {0} registered: OK".format(tts_id)
                        log.info(msg)
                        self.created = True
                        self.identifier = tts_id
                        return True, tts_id
                    else:
                        msg = "Cannot update metadata for new scribe {0}".format(tts_id)
                        log.error(msg)
                        self.created = False
                        self.error_msg = msg
                        return False, msg
                else:
                    msg = "Cannot create the new scribe {0}".format(tts_id)
                    log.error(msg)
                    self.created = False
                    self.error_msg = msg
                    return False, msg
            else:
                msg = "the scribe identifier {0} is not syntax compliant".format(tts_id)
                log.error(msg)
                self.created = False
                self.error_msg = msg
                return False, msg

    def _create_tts_item(self,identifier,content=InternetArchive.DEFAULT_CONTENT_VALUE):
        res = self.add_file_item(identifier, filename=InternetArchive.DEFAULT_FILENAME, content=content)
        if res[0].status_code == 200:
            return True
        else:
            return False

    def update_metadata_tts(self,identifier,metadata):
        res = self.set_item_metadata(identifier,metadata)
        if res == 200:
            msg = "Metadata updated succesfully for item {0}".format(identifier)
            log.info(msg)
            return True, msg
        else:
            msg = "Metadata was not updated for item {0} with code {1}".format(identifier, res)
            log.info(msg)
            return False

    def _validate_id(self,identifier):
        return True
        '''
        if not self.item_exists(identifier) and identifier != '':
            if re.match(r'tts[A-Z]{2}[0-9]{4}', identifier):
                return True
            else:
                return False
        else:
            return False
        '''

    def _generate_id_for_tts(self):
        id_offered = ''
        count = 0
        while not self._validate_id(id_offered) and count < 3:
            id_offered = rstr.xeger(self.REGEX_IDENTIFIER)
            count += 1
        return id_offered

    def tts_update_metadata(self,identifier, metadata):
        if self.set_item_metadata(identifier,metadata):
            log.info("Metadata updated for item {0} with values: {1}".format(identifier,metadata))
            return "Metadata updated for item {0} with values: {1}".format(identifier,metadata)
        else:
            log.error("Cannot update metadata for {0}: Item does not exist".format(identifier))
            return "Cannot update metadata for {0}: Item does not exist".format(identifier)


def check_metadata_registration(Logger):
    Logger.info('Check btserver registration: Begin.')
    metadata = get_metadata(scribe_globals.CONFIG_DIR)
    local_metadata = dict((k, v) for k, v in metadata.items() if v)
    tts = TTSServices(local_metadata)
    upd = None
    my_identifier = local_metadata.get('scanner')
    Logger.info('Loaded {} from scribe metadata'.format(my_identifier))
    try:
        upd = tts.is_metadata_updated(my_identifier, local_metadata)
    except Exception as e:
        Logger.exception('Error in check_metadata_registration')
    # if updated, tell metrics server
    Logger.info('Check btserver registration: Result = {}'.format(upd))
    if upd is not True:
        Logger.info('Metadata is not up to date, pushing to btserver')
        try:
            tts.update_metadata_tts(my_identifier, local_metadata)
            return True
        except Exception:
            Logger.exception('Failed to update metadata fields {} for {}'
                             .format(upd, local_metadata['identifier']))
            return False
    else:
        return True