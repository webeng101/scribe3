from pprint import pprint
from random import randint, random, choice

from kivy.app import App

from ia_scribe.book.scandata import VALID_PAGE_TYPES
from ia_scribe.uix.screens.corrections.note_leafs_view import NoteLeafsView


class NoteLeafsViewApp(App):

    def build(self):
        root = NoteLeafsView()
        root.leafs = self.load_note_leafs()
        root.bind(on_leaf_select=self.on_leaf_select)
        return root

    def load_note_leafs(self):
        page_types = list(VALID_PAGE_TYPES)
        return [
            {'original_image': None,
             'reshoot_image': None,
             'page_number': randint(1, 100),
             'leaf_number': randint(1, 100),
             'page_type': choice(page_types),
             'note': 'note {}'.format(random()),
             'status': randint(0, 1)}
            for _ in range(30)
        ]

    def on_leaf_select(self, note_leafs_view, leaf):
        print('Selected leaf:')
        pprint(leaf)
        print('')


if __name__ == '__main__':
    NoteLeafsViewApp().run()
