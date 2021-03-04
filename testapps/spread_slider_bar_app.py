from kivy.app import App
from kivy.core.window import Window

from ia_scribe.uix.components.toolbars.spread_slider_bar import SpreadSliderBar


class SpreadSliderBarApp(App):

    def build(self):
        Window.clearcolor[:] = [0.92, 0.92, 0.92, 1.0]
        root = SpreadSliderBar(use_tooltips=True)
        root.slider_max = 100
        root.bind(slider_value=self.on_slider_value)
        root.bind(on_slider_value_up=self.on_slider_value_up)
        return root

    def on_slider_value(self, spread_slider_bar, slider_value):
        print('on_slider_value', slider_value)

    def on_slider_value_up(self, spread_slider_bar, slider_value):
        print('on_slider_value_up', slider_value)

    def on_start(self):
        self.root.set_slider_markers([0, 12, 45, 61, 77, 90])


if __name__ == '__main__':
    SpreadSliderBarApp().run()
