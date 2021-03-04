from kivy.app import App

from ia_scribe.uix.screens.capture.leaf_info_panel import LeafInfoPanel


class LeafInfoPanelApp(App):

    def build(self):
        return LeafInfoPanel(
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            leaf_number=10,
            capture_time=0.212321334324,
            width='250dp'
        )


if __name__ == '__main__':
    LeafInfoPanelApp().run()
