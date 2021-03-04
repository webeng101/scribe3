from functools import partial

from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder

kv = '''
FloatLayout:
    pos_hint: {'top': 0.9, 'center_x': 0.5}
    size_hint: None, None
    size: '400dp', '100dp'
    ImageMenuBar:
        pos_hint: {'x': 0, 'center_y': 0.5}
        use_tooltips: True
        orientation: 'left'
    ImageMenuBar:
        pos_hint: {'right': 1, 'center_y': 0.5}
        use_tooltips: True
        orientation: 'right'
'''


class ImageMenuBarApp(App):

    def build(self):
        Window.clearcolor[:] = [1] * 4
        root = Builder.load_string(kv)
        right, left = root.children
        right.bind(on_option_select=partial(self.on_option_select, 'right'))
        left.bind(on_option_select=partial(self.on_option_select, 'left'))
        return root

    def on_option_select(self, side, menu, option):
        print(side, menu, option)


if __name__ == '__main__':
    ImageMenuBarApp().run()
