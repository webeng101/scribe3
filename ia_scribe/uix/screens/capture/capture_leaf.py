from os.path import join, dirname, exists

from kivy.clock import Clock
from kivy.compat import text_type
from kivy.lang import Builder
from kivy.properties import StringProperty, DictProperty
from kivy.uix.gridlayout import GridLayout

from ia_scribe.scribe_globals import LOADING_IMAGE
from ia_scribe.uix.components.poppers.popups import DeleteSpreadPopup, \
    ReshootInsertSpreadPopup

Builder.load_file(join(dirname(__file__), 'capture_leaf.kv'))
_default_stats = {'capture_time': '',
                  'leaf_num': 0,
                  'page_type': 'Normal'}


class CaptureLeaf(GridLayout):

    loading_image = StringProperty(LOADING_IMAGE)
    stats = DictProperty(_default_stats)

    def __init__(self, **kwargs):
        self.capture_screen = kwargs.pop('capture_screen', None)
        super(CaptureLeaf, self).__init__(**kwargs)

    def on_kv_post(self, base_widget):
        super(CaptureLeaf, self).on_kv_post(base_widget)
        panel = self.ids.leaf_info_panel
        panel.fbind('on_edit_start', self._stop_capture_actions)
        panel.fbind('on_edit_end', self._start_capture_actions)
        panel.fbind('on_note_submit', self._on_leaf_note_submit)

    def _stop_capture_actions(self, *args):
        screen = self.capture_screen
        if screen:
            screen.stop_autoshoot_capture()
            screen.disable_capture_actions()

    def _start_capture_actions(self, *args):
        if self.capture_screen:
            self.capture_screen.enable_capture_actions()

    def _on_leaf_note_submit(self, panel, note):
        if self.capture_screen:
            sides = self.capture_screen.get_displayed_sides()
            self.capture_screen.set_leaf_note(sides['foldout'], note)

    def on_stats(self, capture_leaf, stats):
        panel = self.ids.leaf_info_panel
        self._update_leaf_info_panel(panel, stats)

    def _update_leaf_info_panel(self, panel, stats):
        panel.leaf_number = self._to_valid_value(stats, 'leaf_num')
        panel.ppi = self._to_valid_value(stats, 'ppi')
        panel.capture_time = self._to_valid_value(stats, 'capture_time')
        panel.notes = self._to_valid_value(stats, 'notes')

    def _to_valid_value(self, stats, key, not_allowed=(None, '')):
        value = stats.get(key, None)
        if value in not_allowed:
            return None
        if key == 'leaf_num' or key == 'ppi':
            return int(value)
        if key == 'capture_time' or key == 'blurriness':
            return float(value)
        return text_type(value)

    def delete_or_foldout(self):
        screen = self.capture_screen
        spread_slider = screen.spread_slider_bar
        if spread_slider.slider_value == spread_slider.slider_min:
            screen.stop_autoshoot_capture()
            popup = screen.create_popup(popup_cls=ReshootInsertSpreadPopup)
            popup.bind(on_submit=self._on_reshoot_insert_spread_popup_submit)
            popup.open()
        else:
            self.delete_spread()

    def _on_reshoot_insert_spread_popup_submit(self, popup, option):
        if option == popup.OPTION_RESHOOT:
            self.capture_screen.reshoot_cover()
        elif option == popup.OPTION_INSERT:
            self.capture_screen.capture_spread()

    def delete_spread(self):
        self.capture_screen.disable_capture_actions()
        popup = self.capture_screen.create_popup(popup_cls=DeleteSpreadPopup)
        popup.bind(on_submit=self._on_delete_popup_submit)
        popup.open()

    def _on_delete_popup_submit(self, popup, option):
        if option == popup.OPTION_YES:
            self._delete_spread_confirmed(popup)

    def _delete_spread_confirmed(self, popup):
        popup.message = 'Please wait while we delete this spread...'
        popup.set_option_attrs(popup.OPTION_YES, disabled=True)
        popup.set_option_attrs(popup.OPTION_NO, disabled=True)
        capture_screen = self.capture_screen
        book_dir = capture_screen.book_dir
        if not (book_dir and exists(book_dir)):
            popup.message = 'ERROR! Book Dir does not exist'
            popup.set_option_attrs(popup.OPTION_NO, disabled=False)
            popup.auto_dismiss = False
            Clock.schedule_once(
                lambda dt: setattr(popup, 'auto_dismiss', True))
            return
        capture_screen.delete_current_spread_and_rename()
