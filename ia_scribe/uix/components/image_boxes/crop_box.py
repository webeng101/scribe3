from os.path import join, dirname

from kivy.clock import Clock
from kivy.lang.builder import Builder
from kivy.metrics import dp
from kivy.properties import ListProperty, NumericProperty, AliasProperty
from kivy.uix.widget import Widget

from ia_scribe.libraries.vector import Vector

Builder.load_file(join(dirname(__file__), 'crop_box.kv'))


class CropBox(Widget):

    border_color = ListProperty([1, 0, 0, 1.0])
    border_width = NumericProperty('1dp')
    border_collide_width_min = NumericProperty('10dp')
    pos_limit = ListProperty([-float('inf'), -float('inf'),
                              float('inf'), float('inf')])
    size_min = ListProperty([dp(10), dp(10)])
    default_size = ListProperty([dp(120), dp(120)])
    default_pos_hint = ListProperty([0.5, 0.5])

    border_width_modifier = AliasProperty(
        lambda self: 2.0 if self.border_width > 1.0 else 1.0,
        None,
        bind=['border_width'],
        cache=True
    )

    displayed_border_width = AliasProperty(
        lambda self: self.border_width * self.border_width_modifier,
        None,
        bind=['border_width', 'border_width_modifier'],
        cache=True
    )

    def _get_current_collide_border_width(self):
        return max(self.displayed_border_width, self.border_collide_width_min)

    current_collide_border_width = AliasProperty(
        _get_current_collide_border_width,
        None,
        bind=['displayed_border_width', 'border_collide_width_min'],
        cache=True
    )

    container_size = AliasProperty(
        lambda self: Vector(self.pos_limit[2:]) - Vector(self.pos_limit[:2]),
        None,
        bind=['pos_limit'],
        cache=True
    )

    __events__ = ('on_drag_start', 'on_drag', 'on_drag_stop',
                  'on_resize_start', 'on_resize', 'on_resize_stop')

    def __init__(self, **kwargs):
        kwargs.setdefault('size_hint', (None, None))
        self._first_init = True
        self.trigger_update = trigger = Clock.create_trigger(self._update, -1)
        self.fbind('pos_limit', self._update_on_boundaries_change)
        super(CropBox, self).__init__(**kwargs)
        trigger()

    def _update(self, *args):
        if self._first_init:
            self.set_defaults()
            self._first_init = False

    def _update_on_boundaries_change(self, *args):
        self.set_size_and_pos(Vector(self.size), Vector(self.pos))

    def set_defaults(self):
        self.set_size(Vector(self.default_size))
        hint = Vector(self.default_pos_hint)
        pos = (self.container_size - Vector(self.size)) * hint
        pos += Vector(self.pos_limit[:2])
        self.set_pos(pos)

    def set_size_and_pos(self, new_size, new_pos):
        self.set_size(new_size)
        self.set_pos(new_pos)

    def set_size(self, new_size):
        self.size[:] = Vector.clamp(
            new_size,
            Vector(self.size_min),
            Vector(self.pos_limit[2:]) - Vector(self.pos_limit[:2])
        )

    def set_pos(self, new_pos):
        self.pos[:] = Vector.clamp(
            new_pos,
            Vector(self.pos_limit[:2]),
            Vector(self.pos_limit[2:]) - Vector(self.size)
        )

    def collide_with_inner_box(self, x, y):
        width = Vector.ones() * self.current_collide_border_width
        pos = Vector(self.pos)
        return Vector.in_bbox(
            (x, y),
            pos + width,
            pos + Vector(self.size) - width
        )

    def on_touch_down(self, touch):
        if self.disabled and self.collide_point(*touch.pos):
            return True
        data = {'resizing': False}
        in_outer = self.collide_point(*touch.pos)
        if in_outer and not self.collide_with_inner_box(*touch.pos):
            origin, heading = self._find_origin_point_and_heading(touch)
            data['resizing'] = True
            data['origin'] = origin
            data['heading'] = heading
            touch.ud[id(self)] = data
            touch.grab(self)
            self.dispatch('on_resize_start')
            return True
        if in_outer:
            touch.ud[id(self)] = data
            touch.grab(self)
            self.dispatch('on_drag_start')
            return True
        return False

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return False
        uid = id(self)
        if touch.ud[uid]['resizing']:
            origin = touch.ud[uid]['origin']
            heading = touch.ud[uid]['heading']
            delta = Vector(touch.pos) - origin
            pos = heading * (origin + delta)
            pos += (Vector.ones() - heading) * (origin + Vector(self.size))
            self.set_size_and_pos(abs(pos - origin),
                                  Vector.min(pos, origin))
            self.dispatch('on_resize')
            return True
        else:
            self.set_pos(Vector(self.pos) + Vector(touch.dx, touch.dy))
            self.dispatch('on_drag')
            return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            if touch.ud[id(self)].get('resizing', False):
                self.dispatch('on_resize_stop')
            else:
                self.dispatch('on_drag_stop')
            return True

    def _find_origin_point_and_heading(self, touch):
        pos = Vector(self.pos)
        size = Vector(self.size)
        width = self.current_collide_border_width
        top_right = pos + size
        if pos.x <= touch.x <= pos.x + width:
            if pos.y <= touch.y <= pos.y + width:
                return pos + size, Vector.ones()
            elif top_right.y - width <= touch.y <= top_right.y:
                return Vector(pos.x + size.x, pos.y), Vector.ones()
        if top_right.x - width <= touch.x <= top_right.x:
            if pos.y <= touch.y <= pos.y + width:
                return Vector(pos.x, pos.y + size.y), Vector.ones()
            elif top_right.y - width <= touch.y <= top_right.y:
                return Vector(pos), Vector.ones()
        if pos.x + width <= touch.x <= top_right.x - width:
            if pos.y <= touch.y <= pos.y + width:
                return Vector(pos.x, pos.y + size.y), Vector(0.0, 1.0)
            elif top_right.y - width <= touch.y <= top_right.y:
                return Vector(pos), Vector(0.0, 1.0)
        if pos.y + width <= touch.y <= top_right.y - width:
            if pos.x <= touch.x <= pos.x + width:
                return Vector(pos.x + size.x, pos.y), Vector(1.0, 0.0)
            elif top_right.x - width <= touch.x <= top_right.x:
                return Vector(pos), Vector(1.0, 0.0)

    def on_drag_start(self):
        pass

    def on_drag(self):
        pass

    def on_drag_stop(self):
        pass

    def on_resize_start(self):
        pass

    def on_resize(self):
        pass

    def on_resize_stop(self):
        pass
