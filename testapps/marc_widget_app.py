from kivy.config import Config
Config.set('input', 'mouse', 'mouse,disable_multitouch')

from kivy.app import App

from ia_scribe.uix.widgets.marc.MARC import MARCPopup


class MarcWidgetTestApp(App):

    def build(self):
        return MARCPopup()

    def on_start(self):
        self.root_window.size = (1200, 720)


if __name__ == '__main__':
    MarcWidgetTestApp().run()
