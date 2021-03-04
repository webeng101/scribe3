from kivy.graphics import Color, Ellipse, Line
from kivy.properties import ObjectProperty, ListProperty, NumericProperty
from kivy.uix.label import Label
from kivy.uix.relativelayout import RelativeLayout

from ia_scribe.uix.components.labels.labels import RotatedLabel
from ia_scribe.uix.constants import BUTTON_COLORS_TABLE

class PathVisualizationWidget(RelativeLayout):
    data = ObjectProperty()
    elements = ListProperty()
    displacement = NumericProperty(100)
    diameter = NumericProperty(20)
    node_color = ListProperty(BUTTON_COLORS_TABLE['blue']['color_normal'])
    first_node_color = ListProperty(BUTTON_COLORS_TABLE['dark_green']['color_normal'])
    node_label_color = ListProperty([1, 1, 1, 1])
    node_number_color = ListProperty([1, 1, 1, 1])
    drawing_offset_x = NumericProperty(50)

    def __init__(self, **kwargs):
        kwargs['size_hint'] = (None, None)
        super(PathVisualizationWidget, self).__init__(**kwargs)

    def on_data(self, *args, **kwargs):
        self.render()

    def render(self, *args, **kwargs):
        max_x = 0
        nodes, lines = self.data
        self.elements = []
        self.canvas.clear()
        with self.canvas:
            for line in lines:
                Color(*self.node_color)
                Line(points=line, width=self.diameter / 20)

            for node in nodes:

                if node['order'] == 0:
                    Color(*self.first_node_color)
                else:
                    Color(*self.node_color)

                node_circle = Ellipse(pos=(node['x'], node['y']),
                                      size=(self.diameter, self.diameter), )

                if not node['order'] == 0:

                    node_number = Label(text=str(node['order']),
                                        pos=(node['x'] + self.diameter / 2, node['y'] + self.diameter / 2),
                                        bold=False,
                                        color=self.node_number_color)
                    node_number.size = node_number.texture_size
                else:
                    node_number = None


                node_label = RotatedLabel(text=node['name'],
                                          rotation_degrees=45,
                                          pos=(node['x'] + self.diameter / 2, node['y'] + self.diameter + 20),
                                          color=self.node_label_color,
                                          halign='left',
                                          )

                # guarantee elements are kept around
                self.elements.append((node_circle, node_label, node_number))
                max_x = node['x'] + self.diameter + 20 + self.drawing_offset_x

        self.size = (max_x, 250)

    def make_data(self, nodes_list):
        source_x = self.x + self.drawing_offset_x
        source_y = self.height / 2
        nodes = [{'x': source_x + self.displacement * n,
                  'y': source_y,
                  'name': name,
                  'order': n}
                 for n, name in enumerate(nodes_list)]

        lines = []
        for v, w in zip(nodes[:-1], nodes[1:]):
            points = (v['x'] + self.diameter / 2, v['y'] + self.diameter / 2,
                      w['x'] + self.diameter / 2, w['y'] + self.diameter / 2)
            lines.append(points)

        self.data = (nodes, lines)
