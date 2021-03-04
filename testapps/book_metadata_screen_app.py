import shutil
from os.path import join, dirname
from tempfile import mkdtemp

from kivy.app import App
from kivy.logger import Logger

from ia_scribe.book.book import ensure_book_directory
from ia_scribe.uix.screens.metadata.book_metadata_screen import BookMetadataScreen


class BookMetadataScreenApp(App):

    def __init__(self, **kwargs):
        self.temp_book_path = None
        super(BookMetadataScreenApp, self).__init__(**kwargs)

    def build(self):
        return BookMetadataScreen()

    def on_start(self):
        self.root_window.clearcolor = [1, 1, 1, 1]
        self.temp_book_path = directory = mkdtemp(prefix='ia_scribe_')
        Logger.info('App: Using book temp directory: {}'.format(directory))
        metadata = join(dirname(__file__), 'book_directory', 'metadata.xml')
        backend = self.root.backend
        backend.books_dir = directory
        backend.create_new_book()
        ensure_book_directory(backend.book_path)
        shutil.copy(metadata, join(backend.book_path, 'metadata.xml'))
        backend.init()

    def on_stop(self):
        shutil.rmtree(self.temp_book_path)
        Logger.info('App: Removed temp book directory: {}'
                    .format(self.temp_book_path))


if __name__ == '__main__':
    BookMetadataScreenApp().run()
