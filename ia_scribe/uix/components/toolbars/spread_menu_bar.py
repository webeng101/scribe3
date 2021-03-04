from os.path import join, dirname

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import ObjectProperty, BooleanProperty
from kivy.uix.floatlayout import FloatLayout

from ia_scribe.uix.behaviors.tooltip import TooltipControl

Builder.load_file(join(dirname(__file__), 'spread_menu_bar.kv'))


class SpreadMenuBar(TooltipControl, FloatLayout):

    left_type_button = ObjectProperty()
    right_type_button = ObjectProperty()
    left_number_button = ObjectProperty()
    right_number_button = ObjectProperty()
    left_ppi_button = ObjectProperty()
    right_ppi_button = ObjectProperty()
    delete_button = ObjectProperty()

    use_left_menu = BooleanProperty(True)
    use_right_menu = BooleanProperty(True)

    __events__ = ('on_option_select', 'on_type_button_release',
                  'on_number_button_release')

    def __init__(self, **kwargs):
        trigger = Clock.create_trigger(self._update_children_width, -1)
        self.fbind('width', trigger)
        super(SpreadMenuBar, self).__init__(**kwargs)

    def _update_children_width(self, *args):
        rc, mc, lc = self.children
        if self.width >= dp(914):
            self._set_absolute_width(lc, mc, rc)
        else:
            self._set_relative_width(lc, mc, rc)

    def _set_relative_width(self, lc, mc, rc):
        lc.col_default_width = rc.col_default_width = 0
        mc.size_hint_x = 0.175
        lc.size_hint_x = rc.size_hint_x = (1 - mc.size_hint_x) * 0.5
        lc.spacing = mc.spacing = rc.spacing = dp(5)

    def _set_absolute_width(self, lc, mc, rc):
        lc.size_hint_x = rc.size_hint_x = mc.size_hint_x = None
        lc.width = rc.width = dp(377)
        mc.width = dp(160)
        lc.spacing = mc.spacing = rc.spacing = dp(5)
        lc.col_default_width = rc.col_default_width = dp(36)

    def on_disabled(self, instance, disabled):
        if not disabled:
            self.property('use_left_menu').dispatch(self)
            self.property('use_right_menu').dispatch(self)

    def on_option_select(self, side, option):
        pass

    def on_type_button_release(self, side, button):
        pass

    def on_number_button_release(self, side, button):
        pass
