from os.path import join, dirname

from kivy.config import Config

Config.set('graphics', 'width', 1450)
Config.set('graphics', 'height', 850)

from kivy.app import App
from kivy.core.window import Window

from ia_scribe.uix.screens.capture.capture_leaf import CaptureLeaf


class CaptureLeafApp(App):

    def build(self):
        Window.clearcolor[:] = [0.92, 0.92, 0.92, 1.0]
        root = CaptureLeaf(capture_screen=None)
        root.ids.spread_menu_bar.use_tooltips = True
        root.ids.page.source = join(dirname(__file__), 'dummy_page.jpg')
        return root


if __name__ == '__main__':
    CaptureLeafApp().run()
