import json

from ia_scribe.book.metadata import (
    get_sc_metadata,
    get_metadata,
    set_metadata,
)
from kivy.properties import DictProperty
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.scribe_globals import RECENT_USERS_FILE, SCANCENTER_METADATA_DIR
from ia_scribe.uix_backends.widget_backend import WidgetBackend


class UserSwitchScreenBackend(WidgetBackend):

    recent_users = DictProperty()

    def __init__(self, **kwargs):
        self._config = get_sc_metadata()
        self.current_user = self._config['operator'] if self._config and 'operator' in self._config else 'none'
        super(UserSwitchScreenBackend, self).__init__(**kwargs)
        self.recent_users = self._load_users_from_disk()

    def _load_users_from_disk(self):
        try:
            with open(RECENT_USERS_FILE) as f:
                return json.loads(f.read())
        except ValueError as e:
            self.upsert_user(self.current_user, {})
            return self._load_users_from_disk()
        except FileNotFoundError as e:
            self.upsert_user(self.current_user, {})
            return self._load_users_from_disk()

    def _save_users_to_disk(self):
        with open(RECENT_USERS_FILE, 'w+') as f:
            f.write(json.dumps(self.recent_users, indent=4, separators=(',', ': ')))

    def upsert_user(self, email, payload):
        if email in self.recent_users:
            return
        self.recent_users[email] = payload

    def delete_user(self, email):
        if email == self.current_user:
            return False
        del(self.recent_users[email])
        return True

    def get_recent_users_list(self, *args, **kwargs):
        return [{'email': k,
                'payload': v,
                 'is_active_user': self.is_current_user(k) } for k, v in self.recent_users.items()]

    def is_current_user(self, username):
        return username == self.get_current_user()

    def get_current_user(self):
        user = self._config.get('operator', None)
        return user

    def login_user(self, email, payload):
        try:
            self.upsert_user(email, payload)
            self.set_app_operator(email)
            return True, None
        except Exception as e:
            return False, e

    def set_app_operator(self, user):
        config = get_metadata(SCANCENTER_METADATA_DIR)
        config['operator'] = user
        set_metadata(config, SCANCENTER_METADATA_DIR)
        self._config = get_metadata(SCANCENTER_METADATA_DIR)
        runtime_config = Scribe3Configuration()
        runtime_config.set('operator', user)

    def on_recent_users(self, *args, **kwargs):
        self._save_users_to_disk()
