from ia_scribe.uix.components.plots.path_visualization import PathVisualizationWidget

from kivy.app import App
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider

NODES_LIST = ['state 1', 'state2', 'state3', 'state4', 'whatever', 'bisime', 'basame',]


class MyPaintApp(App):
    l = ObjectProperty()

    def build(self):
        parent = BoxLayout(orientation='vertical')
        self.painter = PathVisualizationWidget()
        layout = BoxLayout(size_hint_max_y=100)
        self.c= clearbtn = Button(text='Clear')
        clearbtn.bind(on_release=self.clear_canvas)
        self.r = renderbtn = Button(text='Render')
        renderbtn.bind(on_release=self.redraw_canvas)
        self.l = Label(id='value_label', color=[0, 0, 1, 1])
        s1 = Slider(min=1, max=500, value=100)
        s1.bind(value=self.set_displacement_slider_value)
        s2 = Slider(min=1, max=300, value=30)
        s2.bind(value=self.set_radius_slider_value)
        parent.add_widget(self.painter)
        layout.add_widget(clearbtn)
        layout.add_widget(renderbtn)
        layout.add_widget(s1)
        layout.add_widget(s2)
        layout.add_widget(self.l)
        parent.add_widget(layout)
        self.redraw_canvas()
        return parent

    def clear_canvas(self, *args):
        self.painter.canvas.clear()

    def redraw_canvas(self, *args):
        self.clear_canvas(None)
        self.painter.make_data(NODES_LIST)
        self.painter.render()

    def set_radius_slider_value(self, slider, value):
        self.painter.diameter = value
        self.l.text = str(value)
        self.redraw_canvas()

    def set_displacement_slider_value(self, slider, value):
        self.painter.displacement = value
        self.redraw_canvas()


if __name__ == '__main__':
    MyPaintApp().run()