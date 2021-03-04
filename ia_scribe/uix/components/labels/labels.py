from os.path import join, dirname

from kivy.core.clipboard import Clipboard
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import (
    ListProperty,
    StringProperty,
    NumericProperty,
    AliasProperty,
    ReferenceListProperty,
    BooleanProperty
)
from kivy.graphics import PushMatrix, PopMatrix, Rotate
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.scrollview import ScrollView

from ia_scribe.uix.behaviors.tooltip import TooltipBehavior

Builder.load_file(join(dirname(__file__), 'labels.kv'))


class TooltipLabel(Label):
    pass


class PageNumLabel(ButtonBehavior, Label):

    rgba = ListProperty([0, 0, 0, 0])

    def set_color(self, color):
        colors = {'clear': [0, 0, 0, 0],
                  'gray':  [.765, .765, .765, 1],
                  'green': [.2, .6, 0, 1],
                  'red':   [1, 0, 0, 1],
                  'blue': [0, 0, .5, 1]
                 }
        self.rgba = colors.get(color, colors['clear'])


class BlackLabel(Label):

    def set_width(self, width):
        self.size_hint_x = None
        self.width = width


class CopyLabel(TooltipBehavior, ButtonBehavior, Label):

    icon = StringProperty('icon_copy.png')
    icon_width = NumericProperty('16dp')
    icon_height = NumericProperty('16dp')
    icon_size = ReferenceListProperty(icon_width, icon_height)
    tooltip = StringProperty('Copy to clipboard')

    def _get_icon_pos(self):
        return (
            int(self.right - self.icon_width - self.padding_x),
            int(self.center_y - self.icon_height / 2.0)
        )

    icon_pos = AliasProperty(_get_icon_pos, None,
                             bind=('center_y', 'padding_x', 'right',
                                   'icon_size'))

    def collide_icon_point(self, x, y):
        icon_size = self.icon_size
        ix, iy = self.icon_pos
        return ix <= x <= ix + icon_size[0] and iy <= y <= iy + icon_size[1]

    def collide_mouse_pos(self, x, y):
        wx, wy = self.to_window(*self.icon_pos)
        icon_size = self.icon_size
        return wx <= x <= wx + icon_size[0] and wy <= y <= wy + icon_size[1]

    def on_hovered(self, label, hovered):
        if not hovered:
            self.tooltip = 'Copy to clipboard'

    def on_release(self):
        if self.collide_icon_point(*self.last_touch.pos):
            Clipboard.copy(self.text)
            self.tooltip = 'Copied!'

    def _reposition_tooltip_label(self, *args):
        label = self._tooltip_label
        label_parent = label.parent
        icon_pos = self.icon_pos
        icon_center_x = icon_pos[0] + self.icon_width / 2.0
        icon_y = icon_pos[1] - dp(5)
        center_x, top = self._to_label_parent(icon_center_x, icon_y, self)
        half_label_width = label.width / 2.0
        if center_x + half_label_width > label_parent.width:
            center_x = label_parent.width - half_label_width
        if center_x - half_label_width < 0:
            center_x = half_label_width
        label.center_x = center_x
        if top - label.height < 0:
            top += self.height + label.height
        label.top = top


class RecycleViewLabel(RecycleDataViewBehavior, Label):

    index = NumericProperty()
    selected = BooleanProperty(False)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        self.text = data['identifier']
        self.selected = False

    def apply_selection(self, rv, index, is_selected):
        self.selected = is_selected

    def on_touch_down(self, touch):
        if super(RecycleViewLabel, self).on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos):
            return self.parent.select_with_touch(self.index, touch)


class CheckBoxLabel(BoxLayout):

    active = BooleanProperty(False)
    group = StringProperty()
    allow_no_selection = BooleanProperty(True)
    text = StringProperty()
    text_color = ListProperty([0, 0, 0, 1])


class ScrollableLabel(ScrollView):

    text = StringProperty('')


class RotatedLabel(Label):
    rotation_degrees = NumericProperty(0)

    def __init__(self, **kwargs):
        super(RotatedLabel, self).__init__(**kwargs)

        self.size = self.texture_size

        with self.canvas.before:
            PushMatrix()
            self.rot = Rotate()
            self.rot.angle = self.rotation_degrees
            self.rot.origin = self.center
            self.rot.axis = (0, 0, 1)
        with self.canvas.after:
            PopMatrix()
