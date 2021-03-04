from os.path import join, dirname

from kivy.lang import Builder
from kivy.properties import (
    OptionProperty,
    NumericProperty,
    BooleanProperty,
    StringProperty
)
from kivy.uix.boxlayout import BoxLayout

from ia_scribe.uix.behaviors.tooltip import TooltipControl

Builder.load_file(join(dirname(__file__), 'spread_slider_bar.kv'))


class SpreadSliderBar(TooltipControl, BoxLayout):
    """Widget contains slider for selecting spread, buttons for selecting
    next/previous spread, autoshoot toggle button and autoshoot time input.

    :Events:
        `on_option_select`: option
            Available options: 'previous_spread', 'next_spread',
            'capture_spread'.
        `on_slider_value_up`: value
            Dispatched when `slider_value` is changed by touch up event or
            marker button release or by setting `slider_value` directly. This
            is a better way to know when `slider_value` is selected then
            binding to `slider_value` directly.
    """

    slider_min = NumericProperty()
    slider_max = NumericProperty()
    slider_value = NumericProperty()
    slider_tooltip = StringProperty()

    scan_button_disabled = BooleanProperty()

    autoshoot_min = NumericProperty(0.3)
    autoshoot_max = NumericProperty(30.0)
    autoshoot_value = NumericProperty(4.0)
    autoshoot_state = OptionProperty('normal', options=['normal', 'down'])

    contact_switch_present = BooleanProperty(False)
    contact_switch_toggle_state = OptionProperty('normal', options=['normal', 'down'])

    __events__ = ('on_option_select', 'on_slider_value_up')

    def set_slider_markers(self, markers, tooltip_prefix='Foldout'):
        self.ids.slider.tooltip_prefix = tooltip_prefix
        self.ids.slider.set_markers(markers)

    def on_option_select(self, option):
        pass

    def on_slider_value_up(self, value):
        pass
