# CalibrationWidgetFoldout
# _________________________________________________________________________________________
from os.path import join, dirname

from kivy.lang import Builder
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout

Builder.load_file(join(dirname(__file__), 'foldout_widget.kv'))


class CalibrationWidgetFoldout(BoxLayout):
    scribe_widget = ObjectProperty(None)
    calibration_widget = ObjectProperty(None)
