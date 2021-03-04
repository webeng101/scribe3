import ia_scribe

from kivy.app import App
from kivy.lang import Builder

kv = '''
RecycleButtons:
    viewclass: 'RecycleIconButton'
    size_hint_y: None
    height: self.minimum_height
    SelectableGridLayout:
        cols: 1
        spacing: '5dp'
        default_size: None, dp(40)
        default_size_hint: 1, None
        size_hint_y: None
        height: self.minimum_height
'''


class RecycleButtonsApp(App):

    def build(self):
        menu = Builder.load_string(kv)
        menu.size_hint = (0.5, 0.5)
        menu.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        icon = 'button_send_back.png'
        menu.data = [
            {'key': 'open', 'text': 'Open', 'icon': icon},
            {'text': 'Edit Metadata', 'icon': icon},
            {'text': 'Export Book', 'icon': icon},
            {'text': 'Upload Book to RePublisher', 'icon': icon},
            {'text': 'Delete Book from Scribe', 'icon': icon},
            {'text': 'Cancel', 'icon': icon},
        ]
        menu.bind(on_selection=self._on_selection)
        return menu

    def _on_selection(self, menu, selection):
        print(selection[0])


if __name__ == '__main__':
    RecycleButtonsApp().run()
