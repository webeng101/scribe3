import json
import os
from pprint import pprint

import requests

os.environ['KIVY_GL_BACKEND'] = 'sdl2'

from kivy.app import App
from ia_scribe.uix.components.simple_list.simple_list import SimpleList


DISPLAY_FIELDS = ['title', 'creator', 'repub_state', 'volume']
URL = 'https://archive.org/services/img/{}'


class SimpleListApp(App):

    def build(self):
        root = SimpleList()
        root.leafs = self.load_note_leafs()
        root.bind(on_leaf_select=self.on_leaf_select)
        return root

    def load_note_leafs(self):
        response = requests.get('https://www-judec.archive.org/book/want/do_we_want_it.php?isbn=0123456789&debug=true')
        books_list = json.loads(response.text)['books']
        ret = [
            {'image': URL.format(identifier),
             'key': identifier,
             'value': {k:v for k, v in metadata['metadata'].items() if k in DISPLAY_FIELDS},
             }
            for identifier, metadata in books_list.items()
        ]
        return ret

    def on_leaf_select(self, note_leafs_view, leaf):
        print('Selected leaf:')
        pprint(leaf)
        print('')


if __name__ == '__main__':
    SimpleListApp().run()
