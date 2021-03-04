from kivy.app import App
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout

from ia_scribe.uix.behaviors.tooltip import TooltipControl
from ia_scribe.uix.components.buttons.buttons import MarkerButton


class RootWidget(TooltipControl, FloatLayout):
    pass


class MarkerButtonApp(App):

    def build(self):
        Window.clearcolor = [0.8, 0.8, 0.8, 1]
        root = RootWidget(use_tooltips=True)
        button = MarkerButton(pos_hint={'center_x': 0.5, 'center_y': 0.5},
                              size_hint=(0.5, 0.5))
        button.tooltip = str(button)
        root.add_widget(button)
        return root


if __name__ == '__main__':
    MarkerButtonApp().run()
