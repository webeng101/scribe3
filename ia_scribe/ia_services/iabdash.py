"""
iabdash tools

A wrapper to push data to the iabooks telemetry server

:copyright: (c) 2016 Internet Archive.
:author: <davide@archive.org>
:license: AGPL 3, see LICENSE for more details.
"""

import json
import logging
import os
import sys
import time
import xml.etree.ElementTree as ET

import requests

import ia_scribe.breadcrumbs.other_stats
from ia_scribe import scribe_globals
from ia_scribe.book.metadata import get_metadata
from ia_scribe import utils
from ia_scribe.breadcrumbs import other_stats

Logger = logging.getLogger('IABDASH')
Logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter=logging.Formatter(scribe_globals.LOGGING_FORMAT)
handler.setFormatter(formatter)
Logger.addHandler(handler)


def get_scribe_metadata(meta_dir, file_name='metadata.xml'):
    md = {}
    meta_dir_expanded =  os.path.expanduser(meta_dir)
    meta_file = os.path.join(meta_dir_expanded, file_name)
    if os.path.exists(meta_file):
        tree = ET.parse(meta_file)
        root = tree.getroot()
        collections = []
        for key in root:
            if key.tag == 'collection' and key.text is not None:
                collections.append(key.text)
            else:
                md[key.tag] = key.text
        if collections:
            md['collection'] = collections
    return md


BTSERVER_URL = 'https://iabooks.archive.org/'
API_PATH = 'api/v0.1/events'
URL = BTSERVER_URL + API_PATH
headers = {'Authorization': 'fc6add639e80f76e047f642fe6952168',
           'Content-Type': 'application/json'}


def push_event(event_type, payload, target_type='tts',
               target_id=None, save_data_path=False):
    try:
        scribe_md = get_scribe_metadata(scribe_globals.CONFIG_DIR)
        if target_id is None:
            target_id = scribe_md['scanner']
        from_section = {'user': scribe_md['operator'],
                        'device': 'tts' ,
                        'device_id': scribe_md['scanner']}
        target_section = {'type': target_type, 'id': target_id}
        pload = {}
        for key in payload:
            pload['tts_' + key] = payload[key]
        pload['scanningcenter'] = scribe_md['scanningcenter']
        res = {'from': from_section,
               'target': target_section,
               'event_type': event_type,
               'data': pload}
        x = requests.post(URL,
                          data=json.dumps(res),
                          headers=headers,
                          timeout=scribe_globals.IABDASH_TIMEOUT)
        Logger.info('IABDASH: Pushed event {0} with return code {1}'
                    .format(event_type, str(x)))
        if save_data_path:
            with open(save_data_path, 'a+') as fd:
                file_log = ','.join([time.strftime("%Y-%m-%d|%H:%M:%S"),
                                     json.dumps(res)])
                fd.write(file_log)
                fd.write(os.linesep)
        return x
    except Exception as e:
        Logger.debug('IABDASH: Error {0} in pushing to metrics server. '
                     'Assuming offline mode and skipping...'.format(e))
