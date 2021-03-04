from kivy.app import App
from kivy.lang import Builder
from kivy.properties import ObjectProperty

from ia_scribe.uix.components.file_chooser import FileChooser

kv = '''
FloatLayout:
    GridLayout:
        id: menu
        rows: 1
        size_hint: None, None
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
        col_default_width: '100dp'
        width: self.minimum_width
        ColorButton:
            text: 'Open file'
            on_release: app.start_open_file()
        ColorButton:
            text: 'Save file'
            on_release: app.start_save_file()
        ColorButton:
            text: 'Choose dir'
            on_release: app.start_choose_dir()
    Label:
        size_hint_y: None
        pos_hint: {'center_x': 0.5, 'y': 0.1}
        text: 'Selected: ' + str(app.selection)
        font_size: '20sp'
'''


class FileChooserApp(App):

    selection = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        self.file_chooser = FileChooser()
        super(FileChooserApp, self).__init__(**kwargs)

    def build(self):
        root = Builder.load_string(kv)
        self.file_chooser.bind(on_selection=self.on_file_chooser_selection)
        return root

    def start_open_file(self):
        self.file_chooser.open_file(title='Open file')

    def start_save_file(self):
        self.file_chooser.save_file(title='Save file')

    def start_choose_dir(self):
        self.file_chooser.choose_dir(title='Open directory')

    def on_file_chooser_selection(self, chooser, selection):
        self.selection = selection
        print('Selected:', selection)


if __name__ == '__main__':
    FileChooserApp().run()
