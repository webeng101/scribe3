from kivy.app import App
from kivy.uix.button import Button

from ia_scribe.uix.components.poppers.popups import NewMetadataFieldPopup


class NewMetadataFieldPopupApp(App):

    def __init__(self, **kwargs):
        super(NewMetadataFieldPopupApp, self).__init__(**kwargs)
        self.popup = popup = NewMetadataFieldPopup()
        popup.fbind('on_submit', self._on_form_submit)

    def build(self):
        root = Button(text='Open popup',
                      size_hint=(None, None),
                      pos_hint={'center_x': 0.5, 'center_y': 0.5})
        root.fbind('on_release', self.popup.open)
        return root

    def _on_form_submit(self, popup, data):
        print('Submitted: {}'.format(data))


if __name__ == '__main__':
    NewMetadataFieldPopupApp().run()
