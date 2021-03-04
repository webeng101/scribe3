from kivy.app import App
from kivy.core.window import Window

from ia_scribe.uix.components.toolbars.top_bar import TopBar


class BookMenuBarApp(App):

    def build(self):
        Window.clearcolor = [0.8, 0.8, 0.8, 1.0]
        root = TopBar()
        self._init_top_bar(root)
        return root

    def _init_top_bar(self, root):
        root.username = 'test-username@archive.org'
        root.machine_id = 'test-scanner.archive.org'
        root.pos_hint = {'top': 1}
        root.bind(on_option_select=self._on_top_bar_option_select)

    def _on_top_bar_option_select(self, *args):
        pass


if __name__ == '__main__':
    BookMenuBarApp().run()
