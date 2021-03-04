from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.gridlayout import GridLayout

from ia_scribe.uix.components.buttons.buttons import SortButton


class SortHeader(GridLayout):

    sort_key = StringProperty()
    sort_order = StringProperty('asc')

    _selected_button = None
    '''Current button with state set to 'down'.
    '''

    _internal = False
    '''True if _on_button_state is setting `sort_key` and `sort_order` 
    attributes.
    '''

    def __init__(self, **kwargs):
        self._selected_button = None
        self._internal = False
        super(SortHeader, self).__init__(**kwargs)
        Clock.schedule_once(self._postponed_init, -1)

    def _postponed_init(self, *args):
        for button in self.iter_sort_buttons():
            button.group = str(hash(self))
            button.fbind('state', self._on_button_state)
            if button.state == 'down':
                self._on_button_state(button, button.state)

    def iter_sort_buttons(self):
        for widget in self.children:
            if isinstance(widget, SortButton):
                yield widget

    def _on_button_state(self, button, state):
        if state == 'down':
            self._selected_button = button
            button.fbind('sort_order', self._on_button_sort_order)
            self._internal = True
            self.sort_key = button.key
            self.sort_order = button.sort_order
            self._internal = False
        else:
            button.funbind('sort_order', self._on_button_sort_order)
            self._selected_button = None

    def _on_button_sort_order(self, button, sort_order):
        self.sort_order = sort_order

    def on_sort_key(self, header, sort_key):
        if self._internal:
            return
        for button in self.iter_sort_buttons():
            if button.key == sort_key:
                button.on_release()

    def on_sort_order(self, header, sort_order):
        if self._internal:
            return
        button = self._selected_button
        if button:
            button.sort_order = sort_order
            return
        for button in self.iter_sort_buttons():
            if button.key == self.sort_key:
                button.on_release()
                button.sort_order = sort_order
