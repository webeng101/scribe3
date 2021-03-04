import json
import urllib.request, urllib.parse, urllib.error
from functools import partial

from ia_scribe.ia_services.btserver import get_ia_session
from kivy.clock import Clock
from ia_scribe.exceptions import ScribeException
from ia_scribe.tasks.task_base import TaskBase


def get_cluster_status(self, book):
    Logger = self.logger
    status_msg = 'Geting cluster status for ' + book['identifier']
    Logger.info(status_msg)
    Clock.schedule_once(partial(self.set_status_callback, str(status_msg)))
    try:
        md_url = ('https://archive.org/metadata/{id}/metadata'
                  .format(id=book['identifier']))
        md = json.load(urllib.request.urlopen(md_url))
    except Exception as e:
        Logger.exception('Get cluster status: Error retrieving metadata')
        raise ScribeException('Could not query archive.org for '
                              'repub_state!')
    try:
        if (md is None) or ('result' not in md):
            raise ScribeException('Could not query metadata')

        repub_state = md['result'].get('repub_state')
        status_msg = ('Repub state for {} is {}'
                      .format(str(book['identifier']), str(repub_state)))
        Logger.info('Check QA status: ' + status_msg)
        # Clock.schedule_once(partial(self.set_prop_callback,
        #                             self.status_label,
        #                             status_msg))
        Clock.schedule_once(partial(self.set_status_callback,
                                    str(status_msg)))
        return int(repub_state)
    except:
        return None


class ChangeRepubStateTask(TaskBase):

    item = None

    def __init__(self, **kwargs):
        self.book = kwargs['book']
        self.target_repub_state = kwargs['target_repub_state']
        self.callbacks = kwargs.get('callbacks', [])
        super(ChangeRepubStateTask, self).__init__(logger=kwargs['book'].logger, **kwargs)

    def create_pipeline(self):
        return [
            self._verify_local_preconditions,
            self._load_item,
            self._verify_remote_preconditions,
            self._change_remote_state,
            self._call_back,
        ]

    def _verify_local_preconditions(self):
        self.dispatch_progress('Verifying preconditions')
        if not self.book.identifier:
            raise Exception('This book does not have an identifier')

    def _load_item(self):
        self.dispatch_progress('Loading IA item')
        self.item = get_ia_session().get_item(self.book.identifier)

    def _verify_remote_preconditions(self):
        self.dispatch_progress('Checking all is well with IA')
        if not self.item.exists:
            raise Exception('Item does not exist')
        if self.item.is_dark:
            raise Exception('Item is dark')

    def _change_remote_state(self):
        self.dispatch_progress('Changing remote state')
        self.item.modify_metadata({'repub_state': self.target_repub_state})

    def _call_back(self):
        self.dispatch_progress('Dispatching callbacks')
        for callback in self.callbacks:
            callback(self)


