from os.path import join, dirname

from kivy.lang import Builder
from kivy.properties import StringProperty,OptionProperty, ObjectProperty, BooleanProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout

from ia_scribe.uix.behaviors.tooltip import TooltipControl

Builder.load_file(join(dirname(__file__), 'reshoot_menu_bar.kv'))


class ReShootMenuBar(TooltipControl, BoxLayout):

    EVENT_OPTION_SELECT = 'on_option_select'

    page_type = StringProperty()
    reshoot_menu_disabled = BooleanProperty(False)

    page_type_button = ObjectProperty()

    __events__ = (EVENT_OPTION_SELECT,)

    ppi = NumericProperty()
    '''Set value in ppi button in menu bar.
    '''
    orient = OptionProperty('left', options=['left', 'right'])
    '''Orientation of menu items which can be::

        'left' - page type button is on left side, then note button and others
        'right' - page type button is on far right side and then other widgets

    Defaults to 'left'.
    '''
    def on_option_select(self, option):
        pass

    def on_orientation(self, menu, orient):
        children = self.children[:]
        self.clear_widgets()
        for child in children:
            self.add_widget(child)