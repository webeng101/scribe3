from collections import deque
from os.path import join, dirname
from enum import Enum

from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import (
    StringProperty,
    NumericProperty,
    ObjectProperty,
    BooleanProperty,
    ListProperty,
)

from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.uix.actions.error import ShowErrorAction


Builder.load_file(join(dirname(__file__), 'c2_widget.kv'))


class ConnectionStatus(Enum):
    disconnected = 100
    connecting = 200
    connected = 300
    error = 800
    unknown = 900

class C2Widget(BoxLayout):
    connection_status = ConnectionStatus.unknown
    is_enabled = BooleanProperty(False)
    is_connected = BooleanProperty(False)
    log = StringProperty()
    log_entries = deque([], maxlen=20)
    state = StringProperty('home')
    c2 = ObjectProperty()

    def __init__(self, *args, **kwargs):
        super(C2Widget, self).__init__(**kwargs)
        self.config = Scribe3Configuration()
        self.config.subscribe(self.on_config_update)
        self.on_config_update()

    def attach(self, c2):
        self.c2 = c2
        self.c2.subscribe(self.on_c2_update)
        self.on_c2_update('Initialized')

    def on_c2_update(self, message, *args):
        self.is_connected = self.c2.connection != None \
                            and self.c2.connection.transport.connector.state == 'connected' # cannot find docs on this
        self.log_entries.append(message)
        self._on_log_entries()

    def _on_log_entries(self):
        self.log = '\n'.join([x for x in self.log_entries])

    def on_config_update(self, *args, **kwargs):
        self.is_enabled = self.config.is_true('enable_c2')
        if not self.is_enabled and self.is_connected:
            self.c2.disconnect()

    def on_state(self, *args, **kwargs):
        pass

    def disable_button_action(self, *args):
        self.config.set('enable_c2', not self.is_enabled)

    def connect_button_action(self, *args):
        if self.is_connected:
            self.c2.disconnect()
        else:
            if self.c2:
                self.c2.connect_to_server()
            else:
                self.action = ShowErrorAction(message='The Command and Control system was not properly initialized.\n'
                                                      'Please restart Scribe3 and try again.')
                self.action.display()