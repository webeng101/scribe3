from os.path import join, dirname

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import OptionProperty, ListProperty, StringProperty
from kivy.uix.gridlayout import GridLayout

from ia_scribe.uix.behaviors.tooltip import TooltipControl
from ia_scribe.uix.components.buttons.buttons import TooltipImageButton

Builder.load_file(join(dirname(__file__), 'image_menu_bar.kv'))


class ImageMenuBarButton(TooltipImageButton):

    key = StringProperty()


class ImageMenuBar(TooltipControl, GridLayout):
    '''Menu bar showing options for image.

    :Events:

        `on_option_select`: option
            Dispatched when option is selected from menu.
    '''
    EVENT_OPTION_SELECT = 'on_option_select'

    options = ListProperty(['export', 'view_source', 'rotate'])
    '''List of options which will be displayed in menu bar and it's in left 
    orientation. 
    
    Option are used as key for :class:`ImageMenuBarButton` instance and they 
    must match key values used in kv file.
    '''

    orientation = OptionProperty('left', options=['left', 'right'])
    '''Orientation of menu items which can be:

        'left' - export button, view source file button
        'right' - view source file button, export button

    Defaults to 'left'.
    '''

    background_color = ListProperty([0.92, 0.92, 0.92, 1.0])
    '''Menu background color which defaults to [0.92, 0.92, 0.92, 1.0].
    '''

    __events__ = (EVENT_OPTION_SELECT,)

    def __init__(self, **kwargs):
        self._buttons_stash = {}
        self._options_trigger = Clock.create_trigger(self._update_buttons)
        self.fbind('options', self._options_trigger)
        self.fbind('orientation', self._options_trigger)
        super(ImageMenuBar, self).__init__(**kwargs)

    def _update_buttons(self, *args):
        add_order = []
        for button in self.children[:]:
            self.remove_widget(button)
            self._buttons_stash[button.key] = button
        for option in self.options:
            button = self._buttons_stash.pop(option)
            add_order.append(button)
        if self.orientation == 'right':
            add_order.reverse()
        for button in add_order:
            self.add_widget(button)

    def on_option_select(self, option):
        pass
