from os.path import join, dirname

from kivy.lang import Builder
from kivy.properties import ListProperty, NumericProperty
from kivy.uix.modalview import ModalView

Builder.load_file(join(dirname(__file__), 'overlay_view.kv'))


class OverlayView(ModalView):

    background_color = ListProperty([0, 0, 0, 0, 0])

    _anim_duration = NumericProperty(0)
