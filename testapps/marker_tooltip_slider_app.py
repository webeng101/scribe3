from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout

from ia_scribe.uix.behaviors.tooltip import TooltipControl

KV = '''
RootWidget:
    MarkedTooltipSlider:
        id: slider
        canvas.before:
            Color: 
                rgba: 1, 1, 1, 1
            Rectangle:
                pos: self.pos
                size: self.size
        size_hint: 0.8, None
        height: '50dp'
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
        max: 100
        step: 1
        value: 50
'''


class RootWidget(TooltipControl, FloatLayout):
    pass


class MarkedTooltipSliderApp(App):

    def build(self):
        Window.clearcolor = [0.8, 0.8, 0.8, 1.0]
        root = Builder.load_string(KV)
        root.ids.slider.bind(value=self.on_slider_value)
        return root

    def on_slider_value(self, slider, value):
        slider.tooltip = str(int(value))

    def on_start(self):
        self.root.use_tooltips = True
        slider = self.root.children[0]
        slider.tooltip = str(slider.value)
        slider.set_markers([0, 10, 15, 45, 70, 90])


if __name__ == '__main__':
    MarkedTooltipSliderApp().run()
