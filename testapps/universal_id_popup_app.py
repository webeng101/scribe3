from uuid import uuid4

from kivy.app import App
from kivy.uix.button import Button

from ia_scribe.uix.components.poppers.popups import UniversalIDPopup


class UniversalIDPopupApp(App):

    def __init__(self, **kwargs):
        super(UniversalIDPopupApp, self).__init__(**kwargs)
        self.popup = popup = UniversalIDPopup(
            identifiers=[str(uuid4()) for _ in range(12)]
        )
        popup.fbind('on_submit', self._on_popup_submit)

    def build(self):
        root = Button(text='Open popup',
                      size_hint=(None, None),
                      pos_hint={'center_x': 0.5, 'center_y': 0.5})
        root.fbind('on_release', self.popup.open)
        return root

    def _on_popup_submit(self, popup, identifier):
        print('Selected: {}'.format(identifier))


if __name__ == '__main__':
    UniversalIDPopupApp().run()
