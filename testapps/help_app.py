from kivy.app import App
from kivy.uix.button import Button

from ia_scribe.uix.screens.help.help import Help


class HelpApp(App):

    def __init__(self, **kwargs):
        super(HelpApp, self).__init__(**kwargs)
        self.help = Help()

    def build(self):
        root = Button(text='Open help',
                      size_hint=(None, None),
                      pos_hint={'center_x': 0.5, 'center_y': 0.5})
        root.fbind('on_release', self.help.open)
        return root


if __name__ == '__main__':
    HelpApp().run()
