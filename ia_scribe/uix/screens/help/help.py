import json
from itertools import groupby
from os.path import join, dirname, exists

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget

from ia_scribe.detectors.keyboard_detector import KEY_ACTIONS, SCANCODE_TO_NAME
from ia_scribe.scribe_globals import (
    CAPTURE_ACTION_BINDINGS,
    RESHOOT_ACTION_BINDINGS
)
from ia_scribe.uix.components.overlay.overlay_view import OverlayView

Builder.load_file(join(dirname(__file__), 'help.kv'))


class KeyboardShortcut(BoxLayout):

    key_combination = StringProperty()
    description = StringProperty()


class KeyboardShortcutsPanel(GridLayout):

    def __init__(self, **kwargs):
        super(KeyboardShortcutsPanel, self).__init__(**kwargs)
        Clock.schedule_once(self._postponed_init, -1)

    def _postponed_init(self, *args):
        self._populate_layout(CAPTURE_ACTION_BINDINGS,
                              self.ids.capture_screen_shortcuts)
        self._populate_layout(RESHOOT_ACTION_BINDINGS,
                              self.ids.reshoot_screen_shortcuts)

    def _populate_layout(self, path, layout):
        config = self._load_config(path)
        for shortcut in self._iter_action_shortcuts(config):
            shortcut = KeyboardShortcut(**shortcut)
            layout.add_widget(shortcut)

    def _load_config(self, path):
        if exists(path):
            with open(path) as fd:
                try:
                    return json.load(fd)
                except ValueError:
                    return None
        return None

    def _iter_action_shortcuts(self, config):
        actions = config.get(KEY_ACTIONS, None)
        if actions:
            for action_name, key_actions in actions.items():
                for side, group in groupby(key_actions,
                                           key=lambda x: x.get('side', None)):
                    yield self._create_shortcut(action_name, group, side)

    def _create_shortcut(self, action_name, group, side):
        temp = map(self._create_key_combination, group)
        return {
            'key_combination': ' or '.join(temp),
            'description': self._create_description(action_name, side)
        }

    def _create_description(self, action_name, side=None):
        if side is None:
            return action_name
        return '({}) {}'.format(self._parse_side(side), action_name)

    def _parse_side(self, side):
        if side == 'left':
            return 'Left'
        elif side == 'right':
            return 'Right'
        return 'Unknown'

    def _create_key_combination(self, combo):
        out = []
        mod = combo.get('modifiers', None)
        if mod:
            mod_string = [str(x).upper() for x in mod]
            out += mod_string
        out.append(SCANCODE_TO_NAME.get(combo['scancode'], 'Unknown'))
        return '<{}>'.format('+'.join(out))


class Help(OverlayView):

    target_widget = ObjectProperty(None, allownone=True, baseclass=Widget)

    def __init__(self, **kwargs):
        super(Help, self).__init__(**kwargs)
        self._anim_open = Animation(d=0.4)
        self._anim_open.fbind('on_complete', self._on_anim_open_complete)
        self._anim_dismiss = Animation(d=0.4)
        self._anim_dismiss.fbind('on_complete', self._on_anim_dismiss_complete)
        self._current_anim = None

    def open(self, *largs):
        if self._current_anim:
            return
        if self._window is not None:
            Logger.warning('ModalView: you can only open once.')
            return
        # search window
        self._window = self._search_window()
        if not self._window:
            Logger.warning('ModalView: cannot open view, no window found.')
            return
        self._window.add_widget(self)
        self._window.bind(on_keyboard=self._handle_keyboard)
        self._align_center()
        self.pos = (0, -self.height)
        target_widget = self.target_widget
        if target_widget:
            target_widget.bind(center=self._align_center)
        else:
            self._window.bind(on_resize=self._align_center)
        anim = self._anim_open
        anim.animated_properties.update(self._create_open_properties())
        anim.start(self)
        self._current_anim = anim

    def dismiss(self, *largs, **kwargs):
        if self._current_anim is self._anim_open:
            self._anim_open.cancel(self)
        anim = self._anim_dismiss
        if self._current_anim is anim:
            return
        anim.animated_properties.update(self._create_dismiss_properties())
        anim.start(self)
        self._current_anim = anim

    def _on_anim_open_complete(self, *args):
        self._current_anim = None
        self.dispatch('on_open')

    def _on_anim_dismiss_complete(self, *args):
        self._current_anim = None
        self.dispatch('on_dismiss')
        self._real_remove_widget()

    def _create_open_properties(self):
        target_widget = self.target_widget
        if target_widget:
            center = target_widget.to_window(*target_widget.center)
        else:
            center = self._window.center
        return {'center': center}

    def _create_dismiss_properties(self):
        return {'top': 0}

    def _align_center(self, *l):
        if self.target_widget:
            self.size = self.target_widget.size
        else:
            self.size = self._window.size
        self._update_animation()

    def _update_animation(self, *args):
        anim = self._current_anim
        if anim:
            anim.cancel(self)
            if anim is self._anim_open:
                properties = self._create_open_properties()
            else:
                properties = self._create_dismiss_properties()
            anim.animated_properties.update(properties)
            anim.start(self)

    def _real_remove_widget(self):
        super(Help, self)._real_remove_widget()
        target_widget = self.target_widget
        if target_widget:
            target_widget.unbind(center=self._align_center)
