from kivy.app import App
from kivy.core.window import Window

from ia_scribe.uix.components.toolbars.reshoot_slider_bar import ReShootSliderBar


class ReShootSliderBarApp(App):

    def build(self):
        Window.clearcolor[:] = [0.92, 0.92, 0.92, 1.0]
        root = ReShootSliderBar(use_tooltips=True,
                                switch_button_disabled=False)
        root.slider_max = 100
        root.bind(on_slider_value_up=self.on_slider_value_up)
        root.bind(on_option_select=self.on_option_select)
        return root

    def on_slider_value_up(self, spread_slider_bar, slider_value):
        print('on_slider_value_up', slider_value)

    def on_option_select(self, menu, option):
        print('Selected', option)


if __name__ == '__main__':
    ReShootSliderBarApp().run()
