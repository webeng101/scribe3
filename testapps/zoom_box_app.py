import ia_scribe

from kivy.app import App
from kivy.lang import Builder

kv = '''
FloatLayout:
    RelativeLayout:
        id: parent
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
        size_hint: 0.9, 0.9
        canvas:
            Color:
                rgb: 1, 1, 1
            Rectangle:
                pos: self.to_local(*self.pos)
                size: self.size
        Image:
            id: image
            source: './book_info_panel/cover.jpg'
        ZoomBox:
            id: zoom_box
            texture: image.texture
            pos_limit:
                image.center_x - image.norm_image_size[0] / 2.0, \
                image.center_y - image.norm_image_size[1] / 2.0, \
                image.center_x + image.norm_image_size[0] / 2.0, \
                image.center_y + image.norm_image_size[1] / 2.0,
'''


class ZoomBoxApp(App):

    def build(self):
        return Builder.load_string(kv)


if __name__ == '__main__':
    ZoomBoxApp().run()
