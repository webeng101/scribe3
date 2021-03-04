from kivy.app import App
from kivy.properties import ObjectProperty

from ia_scribe.uix.widgets.rcs.rcs_widget import RCSWidget


class RCSApp(App):
    rcs = ObjectProperty()

    def build(self):
        root = RCSWidget(pos_hint={'x': 0.0, 'center_y': 0.5},
                        size_hint=(1.0, 1.0)
                        )
        return root

    def on_start(self):
        super(RCSApp, self).on_start()
        self.root_window.size = (1000, 600)


if __name__ == '__main__':
    RCSApp().run()
