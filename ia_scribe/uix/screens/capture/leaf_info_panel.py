from os.path import join, dirname

from kivy.lang import Builder
from kivy.properties import OptionProperty, StringProperty, ObjectProperty
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label

Builder.load_file(join(dirname(__file__), 'leaf_info_panel.kv'))


class LeafInfoPanel(GridLayout):

    halign = OptionProperty('left', options=['left', 'right'])
    leaf_number = ObjectProperty(None, allownone=True, baseclass=(int, float))
    # ppi = ObjectProperty(None, allownone=True)
    capture_time = ObjectProperty(None, allownone=True, baseclass=(int, float))
    notes = StringProperty(None, allownone=True)
    blurriness = ObjectProperty(None, allownone=True, baseclass=(int, float))

    __events__ = ('on_edit_start', 'on_edit_end', 'on_note_submit')

    def on_kv_post(self, base_widget):
        super(LeafInfoPanel, self).on_kv_post(base_widget)
        self.ids.note_input.bind(
            note_input_displayed=self._on_note_input_displayed
        )

    def _on_note_input_displayed(self, note_input, note_input_displayed):
        if note_input_displayed:
            self.dispatch('on_edit_start')
        else:
            self.dispatch('on_edit_end')

    def on_edit_start(self):
        pass

    def on_edit_end(self):
        pass

    def on_note_submit(self, note):
        pass


class LeafInfoPanelItem(Label):

    def format_int(self, value):
        return 'NULL' if value is None else str(value)

    def format_float(self, value):
        return 'NULL' if value is None else '{:.2f}'.format(value)

    def format_time(self, value):
        return 'NULL' if value is None else '{:.2f}s'.format(value)

    def format_string(self, value):
        return 'NULL' if value is None else value
