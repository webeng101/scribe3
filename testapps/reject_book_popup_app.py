from pprint import pprint

from kivy.app import App

from ia_scribe.uix.components.buttons.buttons import ColorButton
from ia_scribe.uix.components.poppers.popups import RejectBookPopup


class RejectBookPopupApp(App):

    def build(self):
        button = ColorButton(text='Open popup', size_hint=(None, None),
                             pos_hint={'center_x': 0.5, 'center_y': 0.5})
        button.fbind('on_release', self.show_reject_book_popup)
        return button

    def show_reject_book_popup(self, *args):
        popup = RejectBookPopup()
        popup.fbind('on_submit', self._on_reject_book_popup_submit)
        popup.open()

    def _on_reject_book_popup_submit(self, popup, data):
        print('Submitted:')
        pprint(data)


if __name__ == '__main__':
    RejectBookPopupApp().run()
