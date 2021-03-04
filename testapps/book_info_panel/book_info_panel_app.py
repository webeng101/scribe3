from kivy.app import App
from os.path import join, dirname

from ia_scribe.uix.screens.corrections.book_info_panel import BookInfoPanel


class BookInfoPanelApp(App):

    def build(self):
        return BookInfoPanel(
            cover_image=join(dirname(__file__), 'cover.jpg'),
            title='Flags',
            creator='Kevin Ryan',
            collection='Printdisabled',
            shiptracking='F0310',
            scandate='2017-06-12 12:33',
            scribe_operator='associate-waichung-chan@archive.org',
            republisher_operator='republisher4.shenzhen@archive.org',
            scanner='ttscribe1.hongkong.archive.org'
        )


if __name__ == '__main__':
    BookInfoPanelApp().run()
