from kivy.app import App
from kivy.properties import ObjectProperty

from ia_scribe.uix.widgets.cli.cli_widget import CLIWidgetPopup


class CLIApp(App):
    nm = ObjectProperty()

    def build(self):
        root = CLIWidgetPopup(pos_hint={'x': 0.0, 'center_y': 0.5},
                              size_hint=(1.0, 1.0))
        root.content.bind_to_keyboard_actions()
        return root

    def on_start(self):
        super(CLIApp, self).on_start()
        self.root_window.size = (1000, 600)


if __name__ == '__main__':
    CLIApp().run()
