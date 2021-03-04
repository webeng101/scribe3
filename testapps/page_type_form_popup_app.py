from pprint import pprint

from kivy.app import App

from ia_scribe.uix.components.buttons.buttons import ColorButton
from ia_scribe.uix.components.poppers.popups import PageTypeFormPopup


class PageTypeFormPopupApp(App):

    def build(self):
        self.popup = popup = PageTypeFormPopup(target_anchor_x='right')
        popup.bind(on_submit=self.on_data_submit)
        button = ColorButton(text='Open popup', size_hint=(None, None),
                             pos_hint={'center_x': 0.5, 'center_y': 0.9})
        button.bind(on_release=popup.open)
        popup.target_widget = button
        return button

    def on_data_submit(self, popup, data):
        print('Submitted:')
        pprint(data)


if __name__ == '__main__':
    PageTypeFormPopupApp().run()
