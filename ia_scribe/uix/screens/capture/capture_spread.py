from functools import partial
from os.path import join, dirname, exists

from kivy.clock import Clock
from kivy.compat import text_type
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import StringProperty, DictProperty
from kivy.uix.boxlayout import BoxLayout

from ia_scribe.scribe_globals import LOADING_IMAGE
from ia_scribe.uix.screens.capture.foldout_overlay import FoldoutOverlay
from ia_scribe.uix.components.poppers.popups import DeleteSpreadPopup, ReshootInsertSpreadPopup

Builder.load_file(join(dirname(__file__), 'capture_spread.kv'))
_default_stats = {'capture_time': '',
                  'leaf_num': 0,
                  'page_type': 'Normal'}


class CaptureSpread(BoxLayout):

    loading_image = StringProperty(LOADING_IMAGE)
    left_stats = DictProperty(_default_stats)
    right_stats = DictProperty(_default_stats)
    delete_button_normal = StringProperty('button_delete_spread_normal.png')
    delete_button_foldout = StringProperty('button_delete_spread_normal.png')

    def __init__(self, capture_screen, **kwargs):
        self._foldout_overlay = None
        super(CaptureSpread, self).__init__(**kwargs)
        self.capture_screen = capture_screen
        self.foldout_mode = False

    def on_kv_post(self, base_widget):
        super(CaptureSpread, self).on_kv_post(base_widget)
        for side, panel in (('left', self.ids.left_leaf_info_panel),
                            ('right', self.ids.right_leaf_info_panel)):
            panel.fbind('on_edit_start', self._stop_capture_actions)
            panel.fbind('on_edit_end', self._start_capture_actions)
            panel.fbind('on_note_submit',
                        partial(self._on_leaf_note_submit, side))

    def on_left_stats(self, capture_spread, stats):
        panel = self.ids.left_leaf_info_panel
        self._update_leaf_info_panel(panel, stats)

    def on_right_stats(self, capture_spread, stats):
        panel = self.ids.right_leaf_info_panel
        self._update_leaf_info_panel(panel, stats)

    def _stop_capture_actions(self, *args):
        screen = self.capture_screen
        if screen:
            screen.stop_autoshoot_capture()
            screen.disable_capture_actions()

    def _start_capture_actions(self, *args):
        if self.capture_screen:
            self.capture_screen.enable_capture_actions()

    def _on_leaf_note_submit(self, side, panel, note):
        if self.capture_screen:
            sides = self.capture_screen.get_displayed_sides()
            self.capture_screen.set_leaf_note(sides[side], note)

    def _update_leaf_info_panel(self, panel, stats):
        panel.leaf_number = self._to_valid_value(stats, 'leaf_num')
        # panel.ppi = self._to_valid_value(stats, 'ppi')
        panel.capture_time = self._to_valid_value(stats, 'capture_time')
        panel.notes = self._to_valid_value(stats, 'notes')
        panel.blurriness = self._to_valid_value(stats, 'blurriness')

    def _to_valid_value(self, stats, key, not_allowed=(None, '')):
        value = stats.get(key, None)
        if value in not_allowed:
            return None
        if key == 'leaf_num':
            return int(value)
        if key == 'capture_time' or key == 'blurriness':
            return float(value)
        return text_type(value)

    def delete_or_foldout(self):
        if not self.foldout_mode:
            cameras = self.capture_screen.scribe_widget.cameras
            if cameras.camera_ports['foldout'] is None:
                self.delete_spread()
            else:
                self.enable_foldout_mode()
                button = self.ids.spread_menu_bar.delete_button
                button.source_normal = self.delete_button_foldout
                button.source_down = self.delete_button_foldout
        else:
            self.delete_spread()

    def delete_spread(self):
        screen = self.capture_screen
        screen.disable_capture_actions()
        spread_slider = screen.spread_slider_bar
        if spread_slider.slider_value == spread_slider.slider_min:
            screen.stop_autoshoot_capture()
            popup = screen.create_popup(popup_cls=ReshootInsertSpreadPopup)
            popup.bind(on_submit=self._on_reshoot_insert_spread_popup_submit)
            popup.open()
            return
        popup = screen.create_popup(popup_cls=DeleteSpreadPopup)
        popup.bind(on_dismiss=self._on_delete_popup_dismiss)
        popup.bind(on_submit=self._on_delete_popup_submit)
        popup.open()

    def _on_reshoot_insert_spread_popup_submit(self, popup, option):
        if option == popup.OPTION_RESHOOT:
            self.capture_screen.reshoot_cover()
        elif option == popup.OPTION_INSERT:
            self.capture_screen.calibrate_and_capture_spread()

    def _on_delete_popup_submit(self, popup, option):
        if option == popup.OPTION_YES:
            self._delete_spread_confirmed(popup)

    def _delete_spread_confirmed(self, popup):
        self.disable_foldout_mode()
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

    def _on_delete_popup_dismiss(self, *args):
        if self.foldout_mode:
            self.disable_foldout_mode()

    def enable_foldout_mode(self, *args):
        overlay = self.capture_screen.create_popup(popup_cls=FoldoutOverlay)
        spread_slider = self.capture_screen.spread_slider_bar
        if spread_slider.slider_value == spread_slider.slider_min:
            overlay.ids.left_button.disabled = True
            overlay.ids.left_button.opacity = 0
        self._foldout_overlay = overlay
        image_box_container = self.ids.image_box_container
        overlay.size_hint = (None, None)
        overlay.width = image_box_container.width
        overlay.height = self.height
        self._update_foldout_overlay_pos()
        image_box_container.bind(
            width=overlay.setter('width'),
            center_x=self._update_foldout_overlay_pos
        )
        self.bind(
            height=overlay.setter('height'),
            center_y=self._update_foldout_overlay_pos
        )
        overlay.bind(
            on_option_select=self._on_foldout_replace_option,
            on_open=lambda overlay: setattr(overlay, 'use_tooltips', True),
            on_dismiss=self._on_foldout_overlay_dismiss
        )
        overlay.open()
        Logger.info('CaptureSpread: Enabled foldout mode')
        self.foldout_mode = True

    def disable_foldout_mode(self, *args):
        self.foldout_mode = False
        if self._foldout_overlay:
            self._foldout_overlay.dismiss()
            self._foldout_overlay = None

    def _update_foldout_overlay_pos(self, *args):
        image_box_container = self.ids.image_box_container
        x = image_box_container.to_window(image_box_container.x, 0)[0]
        y = self.to_window(0, self.y)[1]
        window = self.get_root_window()
        pos_hint = {'x': 1.0 * x / window.width, 'y': 1.0 * y / window.height}
        self._foldout_overlay.pos_hint = pos_hint

    def _on_foldout_overlay_dismiss(self, overlay):
        self.unbind(center_y=self._update_foldout_overlay_pos)
        self.ids.image_box_container.unbind(
            center_x=self._update_foldout_overlay_pos
        )
        overlay.use_tooltips = False
        Logger.info('CaptureSpread: Disabled foldout mode')
        self.foldout_mode = False

    def _on_foldout_replace_option(self, overlay, option):
        if option == overlay.OPTION_DELETE:
            overlay.dismiss()
            self.delete_spread()
        elif option == overlay.OPTION_REPLACE_LEFT:
            overlay.dismiss()
            self.capture_screen.capture_foldout('left')
        elif option == overlay.OPTION_REPLACE_RIGHT:
            overlay.dismiss()
            self.capture_screen.capture_foldout('right')
