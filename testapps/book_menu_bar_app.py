from kivy.app import App
from kivy.core.window import Window

from ia_scribe.uix.components.toolbars.book_menu_bar import BookMenuBar


class BookMenuBarApp(App):

    def build(self):
        Window.clearcolor = [0.8, 0.8, 0.8, 1.0]
        root = BookMenuBar(pos_hint={'top': 0.95},
                           downloaded_book=True,
                           use_tooltips=True,
                           use_foldout_buttons=False,
                           identifier='title123456789',
                           title='Really long title ' * 3)
        root.bind(on_option_select=self.on_option_select)
        return root

    def on_option_select(self, bar, option):
        print('Selected: {}'.format(option))


if __name__ == '__main__':
    BookMenuBarApp().run()
