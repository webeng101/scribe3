from os.path import join, dirname

from kivy.lang.builder import Builder
from kivy.properties import (
    ObjectProperty,
    ListProperty,
    NumericProperty,
    AliasProperty
)

from ia_scribe.uix.components.image_boxes.crop_box import CropBox
from ia_scribe.utils import create_mesh_vertices
from ia_scribe.libraries.vector import Vector

DEFAULT_UVS = [0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0]

Builder.load_file(join(dirname(__file__), 'zoom_box.kv'))


class ZoomBox(CropBox):

    angle = NumericProperty(0.0)
    zoom = NumericProperty(2.0)
    zoom_max = NumericProperty(5.0)
    zoom_step = NumericProperty(0.5)
    zoom_pos = ListProperty([0.0, 0.0])
    texture = ObjectProperty(None, allownone=True)

    texture_size = AliasProperty(
        lambda self: Vector(self.texture.size) if self.texture else Vector(),
        None,
        bind=['texture'],
        cache=True
    )

    def _get_uvs_size(self):
        tex_size = self.texture_size
        tz_size = tex_size.safe_div(self.container_size) * Vector(self.size)
        return tz_size.safe_div(tex_size)

    uvs_size = AliasProperty(
        _get_uvs_size,
        None,
        bind=['container_size', 'texture_size', 'size'],
        cache=True
    )

    _vertices = ListProperty(
        create_mesh_vertices((0, 0), (100, 100), DEFAULT_UVS)
    )

    def __init__(self, **kwargs):
        pos_limit = [0.0, 0.0, self.default_size[0], self.default_size[1]]
        kwargs.setdefault('pos_limit', pos_limit)
        self._resizing = False
        self._uvs = None
        self._flag_uvs_model = True
        self._old_zoom_pos_limit = [
            Vector(pos_limit[:2]), Vector(pos_limit[2:])
        ]
        fbind = self.fbind
        fbind('center', self._trigger_update_callback)
        fbind('zoom_pos', self._trigger_update_callback)
        fbind('container_size', self._set_flag_uvs)
        fbind('size', self._set_flag_uvs)
        fbind('texture', self._set_flag_uvs)
        fbind('zoom', self._set_flag_uvs)
        fbind('angle', self._set_flag_uvs)
        fbind('disabled', self._set_flag_uvs)
        super(ZoomBox, self).__init__(**kwargs)
        self._old_zoom_pos_limit = self._get_zoom_pos_limit()

    def set_defaults(self):
        self.set_size(Vector(self.default_size))
        self._set_zoom_pos_from_hint(Vector(self.default_pos_hint))
        self.set_pos(Vector(self.zoom_pos))

    def on_touch_down(self, touch):
        if self.disabled and self.collide_point(*touch.pos):
            return False
        if self.collide_point(*touch.pos):
            heading = 0.0
            if touch.button == 'scrollup':
                heading = -1.0
            elif touch.button == 'scrolldown':
                heading = 1.0
            if heading:
                touch.ud[id(self)] = {'zooming': True}
                touch.grab(self)
                self.zoom = min(self.zoom_max,
                                max(1.0, self.zoom + heading * self.zoom_step))
                self._set_zoom_pos(Vector(self.zoom_pos))
                return True
        value = super(ZoomBox, self).on_touch_down(touch)
        if value and touch.ud[id(self)].get('resizing', False):
            self._resizing = True
        return value

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            if touch.ud[id(self)].get('zooming', False):
                return True
            elif touch.ud[id(self)].get('resizing', False):
                return super(ZoomBox, self).on_touch_move(touch)
            else:
                zoom_pos = Vector(self.zoom_pos) + Vector(touch.dx, touch.dy)
                self._set_zoom_pos(zoom_pos)
                self.set_pos(Vector(self.zoom_pos))
                return True
        return super(ZoomBox, self).on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self \
                and touch.ud[id(self)].get('resizing', False):
            self._resizing = False
        return super(ZoomBox, self).on_touch_up(touch)

    def _trigger_update_callback(self, *args):
        self.trigger_update()

    def _update(self, *args):
        super(ZoomBox, self)._update(*args)
        self._update_vertices()

    def _set_flag_uvs(self, *args):
        self._flag_uvs_model = True
        self.trigger_update()

    def _set_zoom_pos_from_hint(self, hint):
        zoom_pos_limit = self._get_zoom_pos_limit()
        pos = zoom_pos_limit[0]
        top_right = zoom_pos_limit[1] - Vector(self.size)
        zoom_pos = (top_right - pos) * hint + pos
        self._set_zoom_pos(zoom_pos)

    def _update_on_boundaries_change(self, *args):
        zoom_pos = Vector(self.zoom_pos)
        pos = self._old_zoom_pos_limit[0]
        top_right = self._old_zoom_pos_limit[1] - Vector(self.size)
        hint = (zoom_pos - pos).safe_div(top_right - pos)
        self._old_zoom_pos_limit = self._get_zoom_pos_limit()
        self.set_size(Vector(self.size))
        self._set_zoom_pos_from_hint(hint)
        self.set_pos(Vector(self.zoom_pos))

    def set_size_and_pos(self, new_size, new_pos):
        self.set_size(new_size)
        if self._resizing:
            self.set_pos(new_pos)
            self._set_zoom_pos(new_pos)
        else:
            # Dragging the zoom box
            self.set_pos(Vector(self.zoom_pos))

    def _set_zoom_pos(self, new_zoom_pos):
        zoom_pos_limit = self._get_zoom_pos_limit()
        self.zoom_pos[:] = Vector.clamp(
            new_zoom_pos,
            zoom_pos_limit[0],
            zoom_pos_limit[1] - Vector(self.size)
        )

    def _get_zoom_pos_limit(self):
        tz_size = self.uvs_size * self.texture_size
        origin = tz_size * 0.5
        offset = -origin
        offset *= 1.0 / self.zoom
        offset += origin
        offset = offset.safe_div(tz_size) * Vector(self.size)
        scaled_pos = Vector(self.pos_limit[:2]) - offset
        scaled_top_left = scaled_pos + self.container_size + 2 * offset
        return [scaled_pos, scaled_top_left]

    def _update_vertices(self, *args):
        if self.disabled:
            return
        uvs_pos = self._compute_uvs_pos()
        if self._flag_uvs_model:
            self._update_uvs_model()
            self._flag_uvs_model = False
        uvs = self._uvs[:]
        for i in range(0, 8, 2):
            uvs[i] = uvs[i] + uvs_pos.x
            uvs[i + 1] = uvs[i + 1] + uvs_pos.y
        self._vertices[:] = create_mesh_vertices(self.pos, self.size, uvs)

    def _update_uvs_model(self):
        uvs_size = self.uvs_size
        uvs_origin = uvs_size * 0.5
        uvs = [
            0.0, uvs_size[1],
            uvs_size[0], uvs_size[1],
            uvs_size[0], 0.0,
            0.0, 0.0
        ]
        for i in range(0, 8, 2):
            temp = Vector(uvs[i], uvs[i + 1])
            temp -= uvs_origin
            temp *= 1.0 / self.zoom
            temp = temp.rotate(self.angle)
            temp += uvs_origin
            uvs[i] = temp.x
            uvs[i + 1] = temp.y
        self._uvs = uvs

    def _compute_uvs_pos(self):
        cont_size = self.container_size
        size = Vector(self.size)
        tex_size = self.texture_size
        zoom_local_pos = Vector(self.zoom_pos) - Vector(self.pos_limit[:2])
        allowed_size = cont_size - size
        dp_pos = zoom_local_pos.safe_div(allowed_size)
        dp_pos.y = 1.0 - dp_pos.y if allowed_size.y != 0 else 0.0
        tex_zoom_size = tex_size.safe_div(cont_size) * size
        allowed_uvs_size = (tex_size - tex_zoom_size).safe_div(tex_size)
        pos = dp_pos * allowed_uvs_size
        if self.angle % 360 != 0:
            uvs_origin = allowed_uvs_size * 0.5
            pos -= uvs_origin
            pos = pos.rotate(self.angle)
            pos += uvs_origin
        return pos
