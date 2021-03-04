import logging
import sys
import threading
import json
from queue import Queue

import requests
from ia_scribe import scribe_globals
from ia_scribe.book.metadata import get_sc_metadata

Logger = logging.getLogger('Oxcart')
Logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter=logging.Formatter(scribe_globals.LOGGING_FORMAT)
handler.setFormatter(formatter)
Logger.addHandler(handler)


scribe_metadata = get_sc_metadata()
try:
    adapter = scribe_metadata['scanner']
except:
    adapter = None

def put_metric(metric, value, payload=None):
    events_queue.put((adapter, metric, value, payload))

def _push_metric(adapter, metric, value, payload= None):
    API_URL = 'https://iabooks.archive.org/ingestion/v0.1/{adapter}/?metric={metric}&value={value}'
    try:
        if not adapter:
            Logger.debug('An adapter could not be found. '
                         'Does your scribe have a "scanner" value in metadata?')
            return

        concrete_url = API_URL.format(adapter=adapter,
                                      metric=metric,
                                      value=value)
        if payload:
            json_payload = json.dumps(payload, default=str)
            API_URL = '{}{}'.format(API_URL, '&payload={payload}')
            concrete_url = API_URL.format(adapter = adapter,
                                          metric = metric,
                                          value = value,
                                          payload = json_payload)
        else:
            payload = {}


        for key in scribe_globals.DEFAULT_OXCART_PAYLOAD_MD_KEYS:
            if  key not in payload:
                payload[key] = scribe_metadata[key]

        response = requests.get(concrete_url)
        return concrete_url, response
    except Exception as e:
        Logger.debug('Error {0} in pushing to metrics server. '.format(e))
        return concrete_url, e


def ingestion_adapters_worker(events_queue):
    while True:
        Logger.info('Worker alive!')
        adapter, metric, value, payload = events_queue.get()
        response = _push_metric(adapter, metric, value, payload)
        Logger.info('Pushed {} | Response -> {}'.format(*response))
        events_queue.task_done()


events_queue = Queue()
t = threading.Thread(target=ingestion_adapters_worker,
                     name='Oxcart worker',
                     args=(events_queue,))
t.daemon = True
t.start()
