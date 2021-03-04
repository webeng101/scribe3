import time
from pprint import pprint
from random import randint, choice, random
from uuid import uuid4

from kivy.config import Config

Config.set('input', 'mouse', 'mouse,disable_multitouch')

from kivy.app import App

from ia_scribe.uix.screens.library.library_view import LibraryView
from ia_scribe.book.upload_status import UploadStatus


class LibraryListViewApp(App):

    def build(self):
        root = LibraryView(size_hint=(0.9, 0.9),
                           pos_hint={'center_x': 0.5, 'center_y': 0.5})
        root.books[:] = self.load_books()
        root.bind(on_book_select=self.on_book_select)
        return root

    def load_books(self):
        upper_limit = 10 ** 6
        statuses = []
        for status_name in dir(UploadStatus):
            if not status_name.startswith('_'):
                statuses.append(getattr(UploadStatus, status_name).value)
        return [
            {'creator': 'Creator ' + str(randint(0, 100)),
             'title': 'Title ' + str(randint(0, 100)),
             'date_last_modified': time.time() - randint(1000, upper_limit),
             'type': 'item',
             'identifier': str(uuid4())[:12] if random() < 0.8 else None,
             'status': choice(statuses),
             'operator': 'operator{}@archive.org'.format(randint(0, 10)),
             'notes_count': randint(0, 20) if random() < 0.8 else None,
             'leafs': randint(0, 1000),
             'shiptracking': str(uuid4())[:5] if random() < 0.8 else None}
            for _ in range(50)
        ]

    def on_book_select(self, library_view, book):
        print('Selected book:')
        pprint(book)
        print('')

    def on_start(self):
        self.root.ids.library_header.use_tooltips = True


if __name__ == '__main__':
    LibraryListViewApp().run()
