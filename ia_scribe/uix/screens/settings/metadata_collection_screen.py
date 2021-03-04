from functools import partial
from os.path import join, dirname

from kivy.lang import Builder
from kivy.logger import Logger
from kivy.uix.screenmanager import Screen

from ia_scribe.uix.widgets.rcs.rcs_widget import RCSWidget

Builder.load_file(join(dirname(__file__), 'metadata_collection_screen.kv'))

class MetadataCollectionsScreen(Screen):
    pass

