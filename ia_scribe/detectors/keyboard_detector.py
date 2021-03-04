import json

from kivy.event import EventDispatcher

KEY_ACTIONS = 'actions'
KEY_BACKEND = 'backend'
KEY_LAYOUT = 'layout'
KEY_VERSION = 'version'


class KeyboardDetector(EventDispatcher):

    __events__ = ('on_action',)

    def __init__(self, config_path, auto_init=True):
        super(KeyboardDetector, self).__init__()
        self.config_path = config_path
        self._actions = {}
        self._last_action = None
        self._version = None
        self._layout = None
        self._backend = None
        if auto_init:
            self.init()

    @property
    def version(self):
        return self._version

    @property
    def layout(self):
        return self._layout

    @property
    def backend(self):
        return self._backend

    def init(self):
        with open(self.config_path, mode='rb') as fd:
            data = json.load(fd, encoding='utf-8')
        self._layout = data.get(KEY_LAYOUT, None)
        self._backend = data.get(KEY_BACKEND, None)
        self._version = data.get(KEY_VERSION, None)
        self._load_actions(data)
        self.reset()

    def reset(self):
        self._last_action = None

    def load_version(self):
        with open(self.config_path, mode='rb') as fd:
            data = json.load(fd, encoding='utf-8')
        return data.get(KEY_VERSION, None)

    def find_actions_by_name(self, action_name):
        out = []
        for _, action in self._actions.items():
            if action.name == action_name:
                out.append(action)
        return out

    def _load_actions(self, data):
        raise NotImplementedError()

    def on_key_down(self, keycode, scancode, codepoint=None, modifiers=None,
                    **kwargs):
        raise NotImplementedError()

    def on_key_up(self, keycode, scancode, codepoint=None, modifiers=None,
                  **kwargs):
        raise NotImplementedError()

    def on_action(self, action):
        pass


SCANCODE_TO_NAME = {
    4: 'A',
    7: 'D',
    9: 'F',
    10: 'G',
    21: 'R',
    22: 'S',
    23: 'T',
    30: '1',
    31: '2',
    32: '3',
    33: '4',
    34: '5',
    35: '6',
    36: '7',
    37: '8',
    38: '9',
    39: '0',
    40: 'Enter',
    41: 'Escape',
    44: 'Spacebar',
    54: ',',
    55: '.',
    58: 'F1',
    67: 'F10',
    74: 'Home',
    77: 'End',
    79: 'Right',
    80: 'Left',
    81: 'Down',
    82: 'Up',
    88: 'Numpad enter',
    89: 'Numpad1',
    90: 'Numpad2',
    91: 'Numpad3',
    92: 'Numpad4',
    93: 'Numpad5',
    94: 'Numpad6',
    95: 'Numpad7',
    96: 'Numpad8',
    97: 'Numpad9',
    98: 'Numpad0',
    224: 'lctrl',
    225: 'shift',
    229: 'rshift'
}