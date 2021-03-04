from os.path import join, dirname

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import (
    ListProperty,
    StringProperty,
    NumericProperty,
    OptionProperty,
    BooleanProperty,
    ObjectProperty
)
from kivy.uix.behaviors import ButtonBehavior, ToggleButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget
from kivy.vector import Vector

from ia_scribe.uix.behaviors.tooltip import TooltipBehavior
from ia_scribe.uix.constants import BUTTON_COLORS_TABLE

Builder.load_file(join(dirname(__file__), 'buttons.kv'))


def get_button_colors(color):
    mapping = BUTTON_COLORS_TABLE.get(color, None)
    if not mapping:
        mapping = BUTTON_COLORS_TABLE.get('grey')
    return list(mapping.values())


class ColorButton(ButtonBehavior, Label):

    color_normal = ListProperty([0.35, 0.35, 0.35, 1.0])
    color_down = ListProperty([0, 0.28, 0.42, 1])


class ColorToggleButton(ToggleButtonBehavior, ColorButton):
    pass


class ImageButton(ButtonBehavior, Image):

    source_normal = StringProperty(
        'atlas://data/images/defaulttheme/button')

    source_down = StringProperty(
        'atlas://data/images/defaulttheme/button_pressed')

    source = StringProperty('atlas://data/images/defaulttheme/button')

    def __init__(self, **kwargs):
        super(ImageButton, self).__init__(**kwargs)
        self.bind(source_normal=self._update_source)
        self.bind(source_down=self._update_source)
        self.bind(state=self._update_source)
        self._update_source()

    def _update_source(self, *args):
        state = self.state
        self.source = \
            self.source_down if state == 'down' else self.source_normal

    def collide_point(self, x, y):
        norm_w = self.norm_image_size[0]
        norm_h = self.norm_image_size[1]
        norm_x = self.center_x - self.norm_image_size[0] / 2.0
        norm_y = self.center_y - self.norm_image_size[1] / 2.0
        return norm_x <= x < norm_x + norm_w and norm_y <= y <= norm_y + norm_h


class TooltipImageButton(TooltipBehavior, ImageButton):
    pass


class ImageToggleButton(ToggleButtonBehavior, Image):

    source_normal = StringProperty(
        'atlas://data/images/defaulttheme/button')

    source_down = StringProperty(
        'atlas://data/images/defaulttheme/button_pressed')

    source = StringProperty('atlas://data/images/defaulttheme/button')

    def __init__(self, **kwargs):
        super(ImageToggleButton, self).__init__(**kwargs)
        self.bind(source_normal=self._update_source)
        self.bind(source_down=self._update_source)
        self.bind(state=self._update_source)
        self._update_source()

    def _update_source(self, *args):
        state = self.state
        self.source = \
            self.source_down if state == 'down' else self.source_normal

    def collide_point(self, x, y):
        norm_w = self.norm_image_size[0]
        norm_h = self.norm_image_size[1]
        norm_x = self.center_x - self.norm_image_size[0] / 2.0
        norm_y = self.center_y - self.norm_image_size[1] / 2.0
        return norm_x <= x < norm_x + norm_w and norm_y <= y <= norm_y + norm_h


class TooltipToggleButton(TooltipBehavior, ToggleButton):
    pass


class TooltipImageToggleButton(TooltipBehavior, ImageToggleButton):
    pass


class MarkerButton(TooltipBehavior, ButtonBehavior, Widget):

    value = NumericProperty(0)

    color = ListProperty([0, 0.28, 0.42, 1])

    def collide_point(self, x, y):
        if super(MarkerButton, self).collide_point(x, y):
            a = Vector(self.x, self.y)
            b = Vector(self.right, self.y)
            c = Vector(self.center_x, self.top)
            p = Vector(x, y)
            return self.collide_point_in_triangle(p, a, b, c)
        return False

    def collide_mouse_pos(self, x, y):
        wx, wy = self.to_window(*self.pos)
        width, height = self.size
        if wx <= x <= wx + width and wy <= y <= wy + height:
            a = Vector(wx, wy)
            b = Vector(wx + width, wy)
            c = Vector(wx + width / 2.0, wy + height)
            p = Vector(x, y)
            return self.collide_point_in_triangle(p, a, b, c)
        return False

    def collide_point_in_triangle(self, p, a, b, c):
        '''Returns True if vector (point) p is inside of triangle described by
        vectors a, b and c.

        Uses Barycentric Technique to check for collision.
        Link: http://blackpawn.com/texts/pointinpoly/default.html
        '''
        v0 = c - a
        v1 = b - a
        v2 = p - a
        dot00 = v0.dot(v0)
        dot01 = v0.dot(v1)
        dot02 = v0.dot(v2)
        dot11 = v1.dot(v1)
        dot12 = v1.dot(v2)
        inv_denom = 1 / (dot00 * dot11 - dot01 * dot01)
        u = (dot11 * dot02 - dot01 * dot12) * inv_denom
        v = (dot00 * dot12 - dot01 * dot02) * inv_denom
        return u >= 0 and v >= 0 and (u + v) < 1


class SortButton(ToggleButtonBehavior, Label):

    key = StringProperty()
    sort_order = OptionProperty('asc', options=['asc', 'desc'])
    arrow_color = ListProperty([0.6, 0.6, 0.6, 0.0])
    arrow_width = NumericProperty('25dp')
    arrow_padding_x = NumericProperty('10dp')

    _arrow_points = ListProperty()
    _text_x = NumericProperty()
    _text_y = NumericProperty()

    def __init__(self, **kwargs):
        self._trigger_arrow_update = \
            trigger = Clock.create_trigger(self._update_arrow_points, -1)
        fbind = self.fbind
        fbind('center', trigger)
        fbind('sort_order', trigger)
        fbind('arrow_width', trigger)
        fbind('arrow_padding_x', trigger)
        fbind('state', self._update_arrow_opacity)
        super(SortButton, self).__init__(**kwargs)
        trigger()

    def _update_arrow_points(self, *args):
        arrow_width = max(0, self.arrow_width - self.arrow_padding_x)
        arrow_height = self.height * 0.2
        center_x, center_y = self.center
        right = self.right
        padding_x = self.arrow_padding_x / 2.0
        if self.sort_order == 'asc':
            self._arrow_points[:] = [
                right - arrow_width - padding_x, center_y - arrow_height,
                right - padding_x, center_y - arrow_height,
                right - arrow_width / 2.0 - padding_x, center_y + arrow_height
            ]
        else:
            self._arrow_points[:] = [
                right - arrow_width - padding_x, center_y + arrow_height,
                right - padding_x, center_y + arrow_height,
                right - arrow_width / 2.0 - padding_x, center_y - arrow_height
            ]

    def _update_arrow_opacity(self, *args):
        self.arrow_color[3] = float(self.state == 'down')

    def _do_press(self):
        pass

    def on_release(self):
        if self.state == 'normal':
            self._release_group(self)
            self.sort_order = 'asc'
            self.state = 'down'
            return
        self.sort_order = 'desc' if self.sort_order == 'asc' else 'asc'


class SortButtonView(RecycleDataViewBehavior, SortButton):

    index = NumericProperty()

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        super(SortButtonView, self).refresh_view_attrs(rv, index, data)

    def on_release(self):
        super(SortButtonView, self).on_release()
        parent = self.parent
        data = parent.recycleview.data
        for item in data:
            item['state'] = 'normal'
        data[self.index]['sort_order'] = self.sort_order
        data[self.index]['state'] = self.state
        parent.recycleview.refresh_from_data()
        parent.select_with_touch(self.index, self.last_touch)


class IconButton(ButtonBehavior, BoxLayout):

    icon = StringProperty()
    icon_width = NumericProperty('30dp')
    text = StringProperty()
    text_color = ListProperty([1, 1, 1, 1])
    text_bold = BooleanProperty(False)
    text_font_size = NumericProperty('15sp')
    color_normal = ListProperty([0, 0.28, 0.42, .7])
    color_down = ListProperty([0, 0.28, 0.42, 1])


class ToggleIconButton(ToggleButtonBehavior, IconButton):
    pass


class RecycleIconButton(RecycleDataViewBehavior, IconButton):

    index = NumericProperty()

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        self.text = data.get('text', '')
        self.text_color = data.get('text_color', [1, 1, 1, 1])
        self.icon = data.get('icon', '')
        self.set_color(data.get('color', 'grey'))
        self.opacity = data.get('opacity', 1.0)
        self.disabled = data.get('disabled', False)
        self.group = data.get('group')

    def on_touch_up(self, touch):
        if super(RecycleIconButton, self).on_touch_up(touch):
            return self.parent.select_with_touch(self.index, touch)

    def set_color(self, color):
        color_normal, color_down = get_button_colors(color)
        self.color_normal = color_normal
        self.color_down = color_down


class RecycleToggleIconButton(RecycleIconButton, ToggleButtonBehavior):
    pass


class RadioButton(BoxLayout):

    text = StringProperty()
    active = BooleanProperty(False)
    group = ObjectProperty(None, allownone=True)


class TooltipIconButton(TooltipBehavior, IconButton):
    pass


class TooltipColorButton(TooltipBehavior, ColorButton):
    pass


class SpinnerColorButton(ColorButton):
    pass

