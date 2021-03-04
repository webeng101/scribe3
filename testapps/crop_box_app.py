from kivy.app import App
from kivy.lang import Builder

kv = '''
FloatLayout:
    RelativeLayout:
        id: parent
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
        size_hint: 0.8, 0.8
        canvas:
            Color:
                rgb: 0.92, 0.92, 0.92
            Rectangle:
                pos: self.to_local(*self.pos)
                size: self.size
        CropBox:
            size_hint: None, None
            pos_limit: [0, 0, parent.width, parent.height]
'''


class CropBoxApp(App):

    def build(self):
        return Builder.load_string(kv)


if __name__ == '__main__':
    CropBoxApp().run()
