from kivy.app import App

from ia_scribe.uix.components.buttons.buttons import ColorButton
from ia_scribe.uix.components.poppers.popups import CheckBoxPopup


class CheckboxopupApp(App):

    def build(self):
        root = ColorButton(text='Open popup',
                           size_hint=(None, None),
                           pos_hint={'center_x': 0.5, 'center_y': 0.5})
        root.bind(on_release=self.open_popup)
        return root

    def open_popup(self, *args):
        popup = CheckBoxPopup(title='Is it pizza time?',
                              message='Would you lke to order pizza?',
                              checkbox_text='Add a beer',
                              )
        popup.bind(on_submit=self.on_submit)
        popup.open()

    def on_submit(self, popup, value):
        print('Submitted ppi value: {}'.format(value))


if __name__ == '__main__':
    CheckboxopupApp().run()
