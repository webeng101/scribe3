from kivy.app import App
from kivy.core.window import Window

from ia_scribe.uix.components.buttons.buttons import ColorButton
from ia_scribe.uix.screens.capture.foldout_overlay import FoldoutOverlay


class FoldoutOverlayApp(App):

    def build(self):
        Window.clearcolor = [1.0] * 4
        button = ColorButton(text='Open overlay',
                             size_hint=(None, None),
                             pos_hint={'center_x': 0.5, 'center_y': 0.5})
        button.fbind('on_release', self.open_overlay)
        return button

    def open_overlay(self, *args):
        FoldoutOverlay(use_tooltips=True).open()


if __name__ == '__main__':
    FoldoutOverlayApp().run()
