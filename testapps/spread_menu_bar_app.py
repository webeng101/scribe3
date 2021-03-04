from kivy.app import App
from kivy.core.window import Window

from ia_scribe.uix.components.toolbars.spread_menu_bar import SpreadMenuBar


class SpreadMenuBarApp(App):

    def build(self):
        Window.clearcolor[:] = [0.92, 0.92, 0.92, 1.0]
        root = SpreadMenuBar(pos_hint={'top': 1},
                             use_tooltips=True)
        root.bind(on_option_select=self.on_option_select,
                  on_type_button_release=self.on_type_button_release,
                  on_number_button_release=self.on_number_button_release)
        root.left_number_button.set_color('green')
        root.left_number_button.text = '10'
        root.right_number_button.set_color('green')
        root.right_number_button.text = '11'
        return root

    def on_option_select(self, menu, side, option):
        print('Selected', side, option)

    def on_type_button_release(self, menu, side, button):
        print('Selected', side, button)

    def on_number_button_release(self, menu, side, button):
        print('Selected', side, button)


if __name__ == '__main__':
    SpreadMenuBarApp().run()
