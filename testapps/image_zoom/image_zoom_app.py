from kivy.app import App
from kivy.lang import Builder

kv = '''
BoxLayout:
    spacing: '5dp'
    orientation: 'vertical'
    ImageZoom:
        source: 'dummy_page.jpg'
        angle: angle_slider.value
        zoom: zoom_slider.value
        allow_stretch: True
        on_zoom: zoom_slider.value = args[1]
        on_crop_box_change: print('Crop Box: %s' % str(args[1:]))
    BoxLayout:
        size_hint_y: None
        height: '50dp'
        Label:
            text: 'Angle: ' + str(angle_slider.value)
            size_hint_x: None
            width: '200dp'
        Slider:
            id: angle_slider
            value: 0.0
            min: 0.0
            max: 360.0
            step: 90.0
        Label:
            text: 'Zoom: ' + str(zoom_slider.value)
            size_hint_x: None
            width: '200dp'
        Slider:
            id: zoom_slider
            value: 1.5
            min: 1.0
            max: 5.0
            step: 0.5
'''


class ImageZoomApp(App):

    def build(self):
        return Builder.load_string(kv)


if __name__ == '__main__':
    ImageZoomApp().run()
