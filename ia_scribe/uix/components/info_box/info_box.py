from os.path import join, dirname

from kivy.lang import Builder
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout

Builder.load_file(join(dirname(__file__), 'info_box.kv'))

NONE_STR = '-'


class InfoBox(BoxLayout):

    title = StringProperty(NONE_STR)
    value = StringProperty(NONE_STR)
    title_size_hint_x = NumericProperty(1.0)
    title_width = NumericProperty('100dp')
