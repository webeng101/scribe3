from datetime import datetime

from kivy.app import App
from kivy.properties import ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.widget import Widget

BOOK_SLIP_MD = {
    'identifier': 'creatinggeocitie00sawy',
    'datetime': datetime(2018, 7, 1, 17, 32),
    'operator': 'associate-test-name@archive.org',
    'scanner': 'ttscribe12.philippines@archive.org',
    'isbn': '0966288912',
    'boxid': 'IA183475',
    'old_pallet': '1166211',
    'title': 'Creating GeoCities websites',
    'creator': ['Sawyer, Ben', 'Greely, Dave'],
    'pages': 358
}


class BookSlipApp(App):

    slip = ObjectProperty()

    def build(self):
        root = BoxLayout(orientation='vertical', spacing='20dp')
        self.slip = slip = self.build_slip()
        slip.pos_hint = {'center_x': 0.5}
        root.add_widget(self.slip)
        button = Button(text='Export to current directory',
                        size_hint_y=None,
                        height='50dp')
        button.fbind('on_release', self._export_image)
        root.add_widget(button)
        return root

    def build_slip(self):
        return Widget()

    def _export_image(self, *args):
        self.slip.export_image('{}.png'.format(type(self.slip).__name__))
