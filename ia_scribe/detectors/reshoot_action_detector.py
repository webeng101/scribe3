from ia_scribe.detectors.common_actions import A_PAGE_TYPE_ASSERTIONS
from ia_scribe.detectors.keyboard_detector import KeyboardDetector, KEY_ACTIONS

A_SHOOT = 'shoot'
A_SWITCH_CAMERAS = 'switch_cameras'
A_PREVIOUS_LEAF = 'previous_leaf'
A_NEXT_LEAF = 'next_leaf'
A_FIRST_LEAF = 'first_leaf'
A_LAST_LEAF = 'last_leaf'
A_ROTATE_LEAF = 'rotate_leaf'
A_SHOW_PAGE_TYPE = 'show_page_type'
A_SHOW_ORIGINAL_FILE = 'show_original_file'
A_SHOW_RESHOOT_FILE = 'show_reshoot_file'
A_GO_RESCRIBE_SCREEN = 'go_rescribe_screen'

A_CONTROLS = {
    A_SHOOT, A_SWITCH_CAMERAS, A_PREVIOUS_LEAF, A_NEXT_LEAF, A_FIRST_LEAF,
    A_LAST_LEAF, A_ROTATE_LEAF, A_SHOW_PAGE_TYPE, A_SHOW_ORIGINAL_FILE,
    A_SHOW_RESHOOT_FILE, A_GO_RESCRIBE_SCREEN
}

ALL_ACTIONS = A_CONTROLS | A_PAGE_TYPE_ASSERTIONS


class ReShootAction(object):

    def __init__(self, name, scancode):
        self.name = name
        self.scancode = scancode

    def __str__(self):
        return ('<ReShootAction name={!s}, scancode={:d}>'
                .format(self.name, self.scancode))

    def __repr__(self):
        return ('ReShootAction(\'{!s}\', {:d})'
                .format(self.name, self.scancode))


class ReShootActionDetector(KeyboardDetector):

    def _load_actions(self, data):
        actions = self._actions
        data_actions = data[KEY_ACTIONS]
        valid_action_names = ALL_ACTIONS & set(data_actions.keys())
        for action_name in valid_action_names:
            options = data_actions[action_name]
            for option in options:
                scancode = option.get('scancode', None)
                if scancode:
                    actions[scancode] = ReShootAction(action_name, scancode)

    def on_key_down(self, keycode, scancode, codepoint=None, modifiers=None,
                    **kwargs):
        action = self._actions.get(scancode, None)
        if action and not self._last_action:
            self._last_action = action
            self.dispatch('on_action', action)
            return True
        return False

    def on_key_up(self, keycode, scancode, codepoint=None, modifiers=None,
                  **kwargs):
        if self._last_action and self._last_action.scancode == scancode:
            self._last_action = None
            return True
        return False
