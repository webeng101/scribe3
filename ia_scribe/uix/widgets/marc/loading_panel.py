from os.path import join, dirname

from kivy.lang import Builder
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.floatlayout import FloatLayout

from ia_scribe.scribe_globals import LOADING_IMAGE

Builder.load_file(join(dirname(__file__), 'loading_panel.kv'))

class LoadingPanel(FloatLayout):
    loading_image = StringProperty(LOADING_IMAGE)