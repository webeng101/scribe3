from os.path import join, dirname

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout

from ia_scribe.uix.behaviors.tooltip import TooltipControl

Builder.load_file(join(dirname(__file__), 'reshoot_slider_bar.kv'))


class ReShootSliderBar(TooltipControl, BoxLayout):

    EVENT_OPTION_SELECT = 'on_option_select'
    EVENT_SLIDER_VALUE_UP = 'on_slider_value_up'

    slider_min = NumericProperty()
    slider_max = NumericProperty()
    slider_value = NumericProperty()
    slider_tooltip = StringProperty()

    switch_button_disabled = BooleanProperty(False)
    scan_button_disabled = BooleanProperty(False)

    __events__ = (EVENT_OPTION_SELECT, EVENT_SLIDER_VALUE_UP)

    def __init__(self, **kwargs):
        self._switch_cameras_button = None
        self._trigger_switch_button = \
            trigger = Clock.create_trigger(self._on_switch_button_disabled, -1)
        self.fbind('switch_button_disabled', trigger)
        super(ReShootSliderBar, self).__init__(**kwargs)

    def _on_switch_button_disabled(self, *args):
        if self.switch_button_disabled:
            self._switch_cameras_button = button = self.children[1]
            self.remove_widget(button)
        else:
            button = self._switch_cameras_button
            self._switch_cameras_button = None
            self.add_widget(button, index=1)

    def on_option_select(self, option):
        pass

    def on_slider_value_up(self, value):
        pass
