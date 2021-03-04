from os.path import join, dirname

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import (
    OptionProperty,
    VariableListProperty,
    AliasProperty,
    BooleanProperty,
    ListProperty,
    ObjectProperty,
    NumericProperty
)
from kivy.uix.image import Image

from ia_scribe.scribe_globals import LOADING_IMAGE, MISSING_IMAGE
from ia_scribe.uix.components.image_boxes.crop_box import CropBox
from ia_scribe.utils import create_mesh_vertices
from ia_scribe.libraries.vector import Vector

Builder.load_file(join(dirname(__file__), 'image_zoom.kv'))

NON_ZOOM_SOURCES = {LOADING_IMAGE, MISSING_IMAGE}
DEFAULT_UVS = [0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0]


class ImageZoom(Image):

    background_color = ListProperty([.75, .75, .75, 1])
    zoom = NumericProperty(2.0)
    zoom_step = NumericProperty(0.5)
    zoom_max = NumericProperty(5.0)
    angle = NumericProperty(0.0)
    flip_y_axis_for_texture = BooleanProperty(True)
    default_zoom_box_size = ListProperty([dp(120), dp(120)])
    default_zoom_pos_hint = ListProperty([0.5, 0.5])
    zoom_box_border_color = ListProperty([1, 0, 0, 0])
    zoom_box_border_width = NumericProperty('2dp')
    zoom_box_disabled = BooleanProperty(False)
    default_anchor_x = OptionProperty('center',
                                      options=['center', 'left', 'right'])
    padding = VariableListProperty([dp(5), dp(5), dp(5), dp(5)])

    def get_anchor_x(self):
        if self.source in NON_ZOOM_SOURCES:
            return 'center'
        return self.default_anchor_x

    anchor_x = AliasProperty(
        get_anchor_x,
        None,
        bind=['source', 'default_anchor_x'],
        cache=True
    )

    def get_norm_image_size(self):
        if not self.texture or self.allow_stretch and not self.keep_ratio:
            w, h = self.size
            w -= self.padding[0] + self.padding[2]
            h -= self.padding[1] + self.padding[3]
            return max(0.0, w), max(0.0, h)
        w, h = self.size
        angle = self._compute_angle()
        texture_size = self.texture_size_rotated
        ratio = texture_size.x / texture_size.y if texture_size.y != 0 else 1.0
        # ensure that the width is always maximized to the container width
        iw = w if self.allow_stretch else min(w, texture_size.x)
        # calculate the appropriate height
        ih = iw / ratio
        # if the height is too higher, take the height of the container
        # and calculate appropriate width. no need to test further. :)
        if ih > h:
            ih = h if self.allow_stretch else min(h, texture_size.y)
            iw = ih * ratio
        iw -= self.padding[0] + self.padding[2]
        ih -= self.padding[1] + self.padding[3]
        return max(0.0, iw), max(0.0, ih)

    norm_image_size = AliasProperty(
        get_norm_image_size,
        None,
        bind=['texture', 'size', 'allow_stretch', 'keep_ratio', 'padding',
              'texture_size_rotated'],
        cache=True
    )

    def _get_norm_texture_size_ratio(self):
        size = Vector(self.norm_image_size)
        return size.safe_div(self.texture_size_rotated, 1.0)

    norm_size_texture_ratio = AliasProperty(
        _get_norm_texture_size_ratio,
        None,
        bind=['norm_image_size', 'texture', 'angle'],
        cache=True
    )

    def get_norm_image_pos(self):
        norm_image_size = self.norm_image_size
        if self.anchor_x == 'center':
            x = self.center_x - norm_image_size[0] / 2.0
        elif self.anchor_x == 'left':
            x = self.x + self.padding[0]
        else:
            x = self.right - norm_image_size[0] - self.padding[2]
        return x, self.center_y - norm_image_size[1] / 2.0

    norm_image_pos = AliasProperty(
        get_norm_image_pos,
        None,
        bind=['anchor_x', 'center', 'norm_image_size', 'padding'],
        cache=True
    )

    texture_size_rotated = AliasProperty(
        lambda self: abs(Vector(self.texture_size).rotate(self.angle)),
        None,
        bind=['texture_size', 'angle'],
        cache=True
    )

    def _get_current_zoom_box_disabled(self):
        if self.disabled or self.zoom_box_disabled:
            return True
        if not self.source or self.source in NON_ZOOM_SOURCES:
            return True
        return not self.texture

    current_zoom_box_disabled = AliasProperty(
        _get_current_zoom_box_disabled,
        None,
        bind=['disabled', 'zoom_box_disabled', 'source', 'texture'],
        cache=True
    )

    _vertices = ObjectProperty([])

    __events__ = ('on_crop_box_change',)

    def __init__(self, **kwargs):
        self._first_init = True
        trigger = Clock.create_trigger(self._update, -1)
        fbind = self.fbind
        fbind('angle', trigger)
        fbind('norm_image_pos', trigger)
        fbind('norm_image_size', trigger)
        super(ImageZoom, self).__init__(**kwargs)
        Clock.schedule_once(self._postponed_init, -1)

    def _postponed_init(self, *args):
        if self.ids.get('crop_box', None):
            box = self.ids.crop_box
            box.fbind('on_drag_stop', self._dispatch_crop_box_change)
            box.fbind('on_resize_stop', self._dispatch_crop_box_change)

    def set_texture_crop(self, x, y, width, height):
        if self.ids.get('crop_box', None):
            crop = self.transform_texture_crop_to_local(x, y, width, height)
            local_size = Vector(crop[2:])
            local_pos = Vector(crop[:2])
            self.ids.crop_box.set_size_and_pos(local_size, local_pos)

    def transform_local_crop_to_texture(self, x, y, width, height):
        tex_pos = self.transform_local_to_texture(x, y)
        tex_size = Vector(width, height) / self.norm_size_texture_ratio
        if self.flip_y_axis_for_texture:
            tex_pos.y = self.texture_size_rotated[1] - tex_size.y - tex_pos.y
            tex_pos.y = abs(round(tex_pos.y))
        tex_size = abs(Vector(map(round, tex_size)))
        return tex_pos.x, tex_pos.y, tex_size.x, tex_size.y

    def transform_texture_crop_to_local(self, x, y, width, height):
        tex_size = Vector(width, height)
        if self.flip_y_axis_for_texture:
            y = self.texture_size_rotated[1] - tex_size.y - y
        local_size = tex_size * self.norm_size_texture_ratio
        local_pos = self.transform_texture_to_local(x, y)
        return local_pos.x, local_pos.y, local_size.x, local_size.y

    def transform_local_to_texture(self, x, y):
        norm_pos = Vector(self.norm_image_pos)
        # org_norm_size = abs(Vector(self.norm_image_size).rotate(-self.angle))
        # rot_norm_size = org_norm_size.rotate(self.angle)
        # origin = (abs(rot_norm_size) - rot_norm_size) / 2.0
        temp = Vector(x, y) - norm_pos
        # temp -= origin
        # temp = temp.rotate(-self.angle)
        # temp = temp * Vector(self.texture_size).safe_div(org_norm_size)
        temp = temp / self.norm_size_texture_ratio
        return abs(Vector(map(round, temp)))

    def transform_texture_to_local(self, x, y):
        norm_pos = Vector(self.norm_image_pos)
        # org_norm_size = abs(Vector(self.norm_image_size).rotate(-self.angle))
        # rot_norm_size = org_norm_size.rotate(self.angle)
        # origin = (abs(rot_norm_size) - rot_norm_size) / 2.0
        # temp = Vector(x, y) * org_norm_size.safe_div(self.texture_size)
        temp = Vector(x, y) * self.norm_size_texture_ratio
        # temp = temp.rotate(self.angle)
        # temp += origin
        temp += norm_pos
        return temp

    def set_defaults_to_children(self, *args):
        for widget in self._iter_crop_boxes():
            widget.set_defaults()

    def _dispatch_crop_box_change(self, *args):
        if not self.ids.get('crop_box', None):
            return
        box = self.ids.crop_box
        crop = self.transform_local_crop_to_texture(*(box.pos + box.size))
        self.dispatch('on_crop_box_change', *crop)

    def _compute_angle(self):
        return self.angle // 90.0 * 90.0

    def _update(self, *args):
        uvs = DEFAULT_UVS[:]
        if self.angle % 360.0 != 0:
            angle = self._compute_angle()
            origin = Vector(0.5, 0.5)
            for i in range(0, 8, 2):
                temp = Vector(uvs[i], uvs[i + 1]) - origin
                temp = temp.rotate(angle) + origin
                uvs[i] = temp.x
                uvs[i + 1] = temp.y
        self._vertices = create_mesh_vertices(
            self.norm_image_pos,
            self.norm_image_size,
            uvs
        )
        if not self.current_zoom_box_disabled:
            self._update_pos_limits()
            if self._first_init:
                # Setup defaults for children twice, one this frame and the
                # next one to ensure correct pos_limit, size and position
                # of child widgets
                self.set_defaults_to_children()
                Clock.schedule_once(self.set_defaults_to_children)
                self._first_init = False

    def _update_pos_limits(self):
        pos_limit = [
            self.norm_image_pos[0], self.norm_image_pos[1],
            self.norm_image_pos[0] + self.norm_image_size[0],
            self.norm_image_pos[1] + self.norm_image_size[1]
        ]
        for widget in self._iter_crop_boxes():
            widget.pos_limit[:] = pos_limit

    def _iter_crop_boxes(self):
        all_children = self.walk(restrict=True)
        next(all_children)
        for widget in all_children:
            if isinstance(widget, CropBox):
                yield widget

    def on_crop_box_change(self, x, y, width, height):
        pass
