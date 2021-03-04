import json
import os
from ia_scribe.abstract import singleton, Observable
from ia_scribe.scribe_globals import RCS_API_URL, LOCAL_RCS_FILE, REMOTE_RCS_FILE
from ia_scribe.tasks.ia_rcs import RCSSyncTask

@singleton
class RCS(Observable):
    _data = []
    _task_scheduler = None
    observers = set([])

    def __init__(self, task_scheduler=None):
        #super(RCS, self).__init__()
        self._task_scheduler = task_scheduler
        self._load_local_rcs()
        self._verify_default()


    def _validate(self, data):
        if len(data) == 0:
            return False
        return True

    def _load_all_rcs(self):
        file_target = REMOTE_RCS_FILE
        if not os.path.exists(file_target)\
                or os.stat(file_target).st_size == 0:
            self._do_sync()
            return {}
        with open(file_target, 'r') as f:
            try:
                data = json.loads(f.read())
            except Exception as e:
                raise e # for now just raise it, we'll want to manage malformed json
            if self._validate(data):
                return data

    def _load_local_rcs(self):
        file_target = LOCAL_RCS_FILE
        if not os.path.exists(file_target)\
                or os.stat(file_target).st_size == 0:
            return
        with open(file_target, 'r') as f:
            try:
                data = json.loads(f.read())
            except Exception as e:
                raise e  # for now just raise it, we'll want to manage malformed json
            if self._validate(data):
                self._data = data
                self.notify('data_changed')

    def _save_data(self, data, scope='local'):
        file_target = REMOTE_RCS_FILE if scope == 'remote' else LOCAL_RCS_FILE
        with open(file_target, 'w+') as f:
            f.write(json.dumps(data, indent=4, sort_keys=True))
        if scope == 'local':
            self._load_local_rcs()
        elif scope == 'remote':
            self._load_all_rcs()

    def _do_sync(self, *args, **kwargs):
        if not self._task_scheduler:
            return
        sync_task = RCSSyncTask(url=RCS_API_URL,
                                callback=self._receive_sync,
                                )
        self._task_scheduler.schedule(sync_task)

    def schedule_sync(self):
        if not self._task_scheduler:
            return
        sync_task = RCSSyncTask(url=RCS_API_URL,
                                callback=self._receive_sync,
                                periodic=True,
                                interval=2 * 24 * 60 * 60, # every 2 days
                                )
        self._task_scheduler.schedule(sync_task)

    def _receive_sync(self, task):
        data = task._data
        if len(data) > 0:
            if data != self._data:
                self._save_data(data, scope='remote')

    def _verify_default(self):
        if len(self._data) == 0:
            return
        default = self.get_default()
        if len(default) == 0:
            self.set_default(self._data[0])
        elif len(default) == 1:
            return True
        elif len(default) > 1:
            raise Exception('More than one default setting!')

    @staticmethod
    def _parse_collections(collections_string):
        flat_string = collections_string.replace(' ', '')
        ret = flat_string.split(';')
        return ret

    def attach_scheduler(self, task_scheduler):
        self._task_scheduler = task_scheduler

    def filter(self, key, value, data_base=None):
        if data_base is None:
            data_base = self._data.items()
        return [content for content in data_base if content.get(key) == value]

    def flatten(self, data_base, key):
        res = [entry.get(key) for entry in data_base]
        ret = sorted(set(res))
        return ret

    def remote_get_aggregate(self, key):
        remote_data = self._load_all_rcs()
        ret = self.flatten(data_base=remote_data, key=key)
        return ret

    def remote_get_all_in_center(self, center):
        remote_data = self._load_all_rcs()
        ret = self.filter('center', center, remote_data)
        return ret

    def add(self, data):
        if data not in self._data:
            if data.get('rcs_key') in self.flatten(self._data, 'rcs_key'):
                print("Item already in list!")
                return
            set_default = False
            if len(self._data) ==0:
                set_default = True
            if data.get('default') == True:
                set_default = True
            self._data.append(data)
            self._save_data(self._data)
            if set_default:
                self.set_default(data)

    def add_by_id(self, id, name=None):
        remote_data = self._load_all_rcs()
        data = self.get_by_key(key='rcs_key', value=int(id), dataset=remote_data)
        if name:
            data['name'] = name
        self.add(data)

    def as_list(self):
        return self._data

    def delete(self, id):
        self._data.remove(id)
        self._save_data(self._data)

    def rename(self, entry, new_name):
        entry_id = self._data.index(entry)
        self._data[entry_id]['name'] = new_name
        self._save_data(self._data)

    def set_default(self, entry):
        previous_default = self.get_default()
        if len(previous_default) > 0:
            if previous_default[0] == entry:
                print('already a default')
                return
            previous_default_id = self._data.index(previous_default[0])
            self._data[previous_default_id]['default'] = False
        entry_id = self._data.index(entry)
        self._data[entry_id]['default'] = True
        self._save_data(self._data)

    def get_default(self, wrap=True):
        ret = self.filter('default', True, self._data)
        if not wrap:
            if len(ret) > 0:
                ret = ret[0]
        return ret

    def get_current_collections(self):
        current = self.get_default()
        collections = self._parse_collections(current.get('collections'))
        return collections

    def get_collections_by_name(self, name):
        data = self.filter('name', name, self._data)[0]
        collections = self._parse_collections(data.get('collections'))
        return collections

    def get_by_name(self, name):
        return self.get_by_key('name', name)

    def get_by_key(self, key, value, dataset=None):
        if not dataset:
            dataset = self._data
        data = self.filter(key, value, dataset)
        if len(data)>0:
            data = data[0]
        return data

    def get_current_collection_sets(self):
        return self.flatten(self._data, 'name')