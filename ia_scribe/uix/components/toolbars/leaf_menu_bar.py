from os.path import join, dirname

from kivy.lang import Builder
from kivy.properties import (ListProperty, OptionProperty, StringProperty,
                             NumericProperty)
from kivy.uix.gridlayout import GridLayout

from ia_scribe.uix.behaviors.tooltip import TooltipControl

Builder.load_file(join(dirname(__file__), 'leaf_menu_bar.kv'))

OPTION_VIEW_SOURCE = 'view_source'
OPTION_ROTATE = 'rotate'
OPTION_EXPORT = 'export'
OPTION_INSERT = 'insert'
OPTION_NOTE = 'note'
OPTION_PAGE_ATTRS = 'page_attrs'


class LeafMenuBar(TooltipControl, GridLayout):
    '''Menu bar showing options for book's leaf.

    :Events:

        `on_option_select`: option
            Dispatched when option is selected from menu.
    '''

    page_type = StringProperty()
    '''Set text of page type button in menu bar.
    '''

    ppi = NumericProperty()
    '''Set value in ppi button in menu bar.
    '''

    background_color = ListProperty([1.0, 1.0, 1.0, 1.0])
    '''Menu background color which defaults to white.
    '''

    orientation = OptionProperty('left', options=['left', 'right'])
    '''Orientation of menu items which can be::

        'left' - page type button is on left side, then note button and others
        'right' - page type button is on far right side and then other widgets

    Defaults to 'left'.
    '''

    __events__ = ('on_option_select',)

    def on_orientation(self, menu, orientation):
        children = self.children[:]
        self.clear_widgets()
        for child in children:
            self.add_widget(child)

    def on_option_select(self, option):
        pass
