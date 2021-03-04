from ia_scribe.detectors.common_actions import A_PAGE_TYPE_ASSERTIONS
from ia_scribe.detectors.keyboard_detector import KeyboardDetector, KEY_ACTIONS

A_SHOOT = 'shoot'
A_TOGGLE_AUTOSHOOT = 'toggle_autoshoot'
A_RESHOOT = 'reshoot'
A_DELETE_SPREAD = 'delete_spread'
A_DELETE_SPREAD_CONFIRM = 'delete_spread_confirm'
A_DELETE_SPREAD_OR_FOLDOUT = 'delete_spread_or_foldout'
A_PREVIOUS_SPREAD = 'previous_spread'
A_NEXT_SPREAD = 'next_spread'
A_PREVIOUS_FOLDOUT_SPREAD = 'previous_foldout_spread'
A_NEXT_FOLDOUT_SPREAD = 'next_foldout_spread'
A_SHOW_ORIGINAL_FILE = 'show_original_file'
A_GO_MAIN_SCREEN = 'go_main_screen'
A_GO_CAPTURE_COVER = 'go_capture_cover'
A_GO_LAST_SPREAD = 'go_last_spread'
A_SHOW_PAGE_ATTRS = 'show_page_attributes'

A_CONTROLS = {
    A_SHOOT, A_TOGGLE_AUTOSHOOT, A_RESHOOT, A_DELETE_SPREAD,
    A_DELETE_SPREAD_CONFIRM, A_DELETE_SPREAD_OR_FOLDOUT, A_PREVIOUS_SPREAD,
    A_NEXT_SPREAD, A_PREVIOUS_FOLDOUT_SPREAD, A_NEXT_FOLDOUT_SPREAD,
    A_SHOW_ORIGINAL_FILE, A_GO_MAIN_SCREEN, A_GO_CAPTURE_COVER,
    A_GO_LAST_SPREAD, A_SHOW_PAGE_ATTRS,
}

ALL_ACTIONS = A_CONTROLS | A_PAGE_TYPE_ASSERTIONS


class CaptureAction(object):

    def __init__(self, name, scancode, modifiers=None, side=None):
        self.name = name
        self.scancode = scancode
        self.modifiers = modifiers or []
        self.side = side

    def __str__(self):
        return ('<CaptureAction name={!s}, scancode={:d}, '
                'modifiers={!s}, side={!s}>'
                .format(self.name, self.scancode, self.modifiers, self.side))

    def __repr__(self):
        return ('CaptureAction(\'{!s}\', {:d}, {!s}, \'{!s}\')'
                .format(self.name, self.scancode, self.modifiers, self.side))


class CaptureActionDetector(KeyboardDetector):

    def _load_actions(self, data):
        actions = self._actions
        data_actions = data[KEY_ACTIONS]
        valid_action_names = ALL_ACTIONS & set(data_actions.keys())
        for action_name in valid_action_names:
            options = data_actions[action_name]
            for option in options:
                scancode = option.get('scancode', None)
                if scancode:
                    modifiers = option.get('modifiers', [])
                    side = option.get('side', None)
                    action = CaptureAction(action_name, scancode,
                                           modifiers, side)
                    key = (scancode, tuple(modifiers))
                    actions[key] = action

    def on_key_down(self, keycode, scancode, codepoint=None, modifiers=None,
                    **kwargs):
        new_modifiers = set(modifiers) if modifiers else set()
        if new_modifiers:
            new_modifiers.discard('numlock')
            new_modifiers.discard('capslock')
        key = (scancode, tuple(new_modifiers))
        if scancode == 98 and self._backend == 'sdl2':
            # This is a workaround for Kivy 1.9.1 bug
            # When pressing numpad_0 modifiers ['alt'] is also passed and
            # therefore there is not difference when only numpad_0 is pressed
            # and when numpad_0 and alt key are pressed.
            # Since detector is not using alt in this case, 'alt' is removed
            # from modifiers.
            if 'alt' in new_modifiers and 'ctrl' in new_modifiers:
                key = (scancode, ('ctrl',))
            elif 'alt' in new_modifiers:
                key = (scancode, tuple())
        action = self._actions.get(key, None)
        if action and not self._last_action:
            self._last_action = action
            self.dispatch('on_action', action)
            return True

    def on_key_up(self, keycode, scancode, codepoint=None, modifiers=None,
                  **kwargs):
        if self._last_action and self._last_action.scancode == scancode:
            self._last_action = None
            return True
        return False
