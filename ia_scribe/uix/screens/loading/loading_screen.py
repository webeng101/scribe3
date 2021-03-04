from os.path import join, dirname

from kivy.lang import Builder
from kivy.uix.screenmanager import Screen

Builder.load_file(join(dirname(__file__), 'loading_screen.kv'))


class LoadingScreen(Screen):
    pass
