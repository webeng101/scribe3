from collections import deque
from itertools import zip_longest

from kivy.clock import Clock
from kivy.compat import text_type
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivy.uix.slider import Slider

from ia_scribe.uix.behaviors.tooltip import TooltipBehavior
from ia_scribe.uix.components.buttons.buttons import MarkerButton


class TooltipSlider(TooltipBehavior, Slider):
    '''Slider which shows tooltip when mouse indicator is over slider's knob
    or when touch starts moving the knob.
    '''

    touch_moving = BooleanProperty(False)

    __events__ = ('on_value_up',)

    def __init__(self, **kwargs):
        self._old_value = 0
        self._touch_down = False
        self.fbind('touch_moving', self._update_tooltip_label)
        super(TooltipSlider, self).__init__(**kwargs)

    def on_touch_down(self, touch):
        self._old_value = self.value
        self._touch_down = True
        if super(TooltipSlider, self).on_touch_down(touch):
            if not touch.is_mouse_scrolling:
                self.touch_moving = self.hovered = True
            elif self.collide_mouse_pos(*Window.mouse_pos):
                self.hovered = True
            else:
                self.hovered = False
            return True
        self._touch_down = False

    def on_touch_move(self, touch):
        if super(TooltipSlider, self).on_touch_move(touch):
            self._reposition_tooltip_label()
            return True

    def on_touch_up(self, touch):
        if super(TooltipSlider, self).on_touch_up(touch):
            self.touch_moving = False
            if self._old_value != self.value:
                self.dispatch('on_value_up', self.value)
            self._touch_down = False
            return True
        elif touch.is_mouse_scrolling and self.collide_point(*touch.pos):
            if self._old_value != self.value:
                self.dispatch('on_value_up', self.value)
            self._touch_down = False
            return True

    def on_value(self, slider, value):
        if not self._touch_down:
            self.dispatch('on_value_up', value)

    def on_value_pos(self, slider, pos):
        if not self.disabled:
            self.hovered = self.collide_mouse_pos(*Window.mouse_pos)

    def collide_mouse_pos(self, x, y):
        # Collide with slider's knob
        _, center_y = self.to_window(0, self.center_y)
        half_height = self.cursor_height / 2.0
        if not(center_y - half_height <= y <= center_y + half_height):
            return False
        pos = self.to_window(*self.value_pos)
        half_width = self.cursor_width / 2.0
        if not(pos[0] - half_width <= x <= pos[0] + half_width):
            return False
        return True

    def _update_tooltip_label(self, *args):
        label_parent = self._tooltip_label.parent
        hovered, moving = self.hovered, self.touch_moving
        if (hovered or moving) and not (self.disabled or label_parent):
            window = self.get_tooltip_window()
            if window:
                self._tooltip_label.bind(size=self._reposition_tooltip_label)
                window.add_widget(self._tooltip_label)
                self._reposition_tooltip_label()
        elif (not(hovered or moving) or self.disabled) and label_parent:
            self._tooltip_label.unbind(size=self._reposition_tooltip_label)
            label_parent.remove_widget(self._tooltip_label)

    def _reposition_tooltip_label(self, *args):
        super(TooltipSlider, self)._reposition_tooltip_label()
        label = self._tooltip_label
        label_parent = label.parent
        center_x, _ = self._to_label_parent(self.value_pos[0], 0, self)
        half_label_width = label.width / 2.0
        if center_x + half_label_width > label_parent.width:
            center_x = label_parent.width - half_label_width
        if center_x - half_label_width < 0:
            center_x = half_label_width
        label.center_x = center_x

    def on_value_up(self, value):
        pass


class MarkedTooltipSlider(TooltipSlider):

    marker_size = ListProperty([dp(16), dp(16)])
    tooltip_prefix = StringProperty()

    _cache = deque(maxlen=500)

    def __init__(self, **kwargs):
        self._marker_buttons = []
        trigger = Clock.create_trigger(self._reposition_marker_buttons, -1)
        fbind = self.fbind
        fbind('pos', trigger)
        fbind('width', trigger)
        fbind('min', trigger)
        fbind('max', trigger)
        fbind('padding', trigger)
        super(MarkedTooltipSlider, self).__init__(**kwargs)

    def set_markers(self, markers):
        new_widgets = []
        handled = 0
        for marker, button in zip_longest(markers, self._marker_buttons):
            if marker is None:
                break
            elif button is None:
                button = self._create_marker_button()
                new_widgets.append(button)
            self._update_marker_button(button, marker)
            handled += 1
        for button in new_widgets:
            self._marker_buttons.append(button)
            self.add_widget(button, canvas='before')
        self._remove_marker_buttons(len(self._marker_buttons) - handled)
        self._reposition_marker_buttons()

    def on_touch_down(self, touch):
        button = self.find_marker_button(*touch.pos)
        if button and button.on_touch_down(touch):
            touch.ud[id(self)] = button
            return True
        return super(MarkedTooltipSlider, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        button = touch.ud.get(id(self), None)
        if button and button.on_touch_move(touch):
            return True
        return super(MarkedTooltipSlider, self).on_touch_move(touch)

    def on_touch_up(self, touch):
        button = touch.ud.pop(id(self), None)
        if button and button.on_touch_up(touch):
            return True
        return super(MarkedTooltipSlider, self).on_touch_up(touch)

    def find_marker_button(self, x, y):
        buttons = self._marker_buttons
        if not buttons:
            return None
        low, high = 0, len(buttons)
        while low < high:
            mid = (high + low) // 2
            button = buttons[mid]
            if x < button.x:
                high = mid
                continue
            elif x > button.right:
                low = mid + 1
                continue
            else:
                return button

    def _create_marker_button(self):
        if self._cache:
            button = self._cache.pop()
            button.size = self.marker_size
        else:
            button = MarkerButton(size_hint=(None, None),
                                  size=self.marker_size)
        button.fbind('on_release', self._on_marker_button_release)
        return button

    def _update_marker_button(self, button, value):
        button.value = value
        prefix = self.tooltip_prefix
        if prefix:
            button.tooltip = text_type('{}: {}').format(prefix, value)
        else:
            button.tooltip = text_type(prefix)

    def _remove_marker_buttons(self, count):
        on_release_method = self._on_marker_button_release
        while count > 0:
            button = self._marker_buttons.pop()
            button.funbind('on_release', on_release_method)
            self.remove_widget(button)
            self._cache.append(button)
            count -= 1

    def _reposition_marker_buttons(self, *args):
        x, y = self.x + self.padding, self.y
        width = self.width - 2 * self.padding
        max_length = self.max - self.min
        for widget in self._marker_buttons:
            center_x = x
            if max_length != 0:
                length = widget.value - self.min
                center_x += width * (1.0 * length / max_length)
            widget.center_x = center_x
            widget.y = y

    def _on_marker_button_release(self, marker_button):
        self.value = marker_button.value
        marker_button.hovered = False
        self.dispatch('on_value_up', self.value)

    def on_marker_size(self, slider, size):
        for button in self._marker_buttons:
            button.size = size
