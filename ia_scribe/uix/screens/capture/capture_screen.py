import datetime
import glob
import os
import shutil
import webbrowser
from collections import OrderedDict
from functools import partial
from os.path import join, basename, dirname
from pprint import pformat

from PIL import Image
from kivy import Logger
from kivy.cache import Cache
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import ObjectProperty, NumericProperty, StringProperty
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen

from ia_scribe import scribe_globals
from ia_scribe.cameras import camera_system
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.detectors.capture_action_detector import CaptureActionDetector
from ia_scribe.book.metadata import get_metadata, set_metadata
from ia_scribe.book.scandata import (
    ScanData,
    SIDE_TO_DEGREE,
    KEY_NOTE,
    PT_NORMAL,
    PT_FOLDOUT,
    PT_COLOR_CARD,
    PT_COVER,
)
from ia_scribe.ia_services import btserver
from ia_scribe.ia_services.iabdash import push_event
from ia_scribe.tasks.book import BookTask
from ia_scribe.uix.actions.book_reset import ResetBookActionMixin
from ia_scribe.uix.actions.book_delete import DeleteBookActionMixin
from ia_scribe.uix.actions.book_upload import UploadBookWrapper
from ia_scribe.uix.actions.send_to_station import SendToStationActionMixin
from ia_scribe.uix.behaviors.tooltip import TooltipScreen
from ia_scribe.uix.widgets.export.book_export import BookExport
from ia_scribe.uix.components.buttons.buttons import ColorButton
from ia_scribe.uix.screens.capture.capture_action_handler import CaptureActionHandler
from ia_scribe.uix.screens.capture.capture_leaf import CaptureLeaf
from ia_scribe.uix.screens.capture.capture_spread import CaptureSpread
from ia_scribe.uix.components.file_chooser import FileChooser

from ia_scribe.uix.components.poppers.popups import (
    BookNotesPopup,
    EditPPIPopup,
    CalibrateCamerasPopup,
    QuestionPopup,
    InfoPopup,
    PageTypeFormPopup,
    CaptureFailurePopup,
    ReshootInsertSpreadPopup,
    ThreeOptionsQuestionPopup,
)
from ia_scribe.book.upload_status import UploadStatus
from ia_scribe.utils import (
    setup_logger,
    teardown_logger,
    read_book_identifier,
    has_free_disk_space,
    get_string_value_if_list,
    convert_scandata_angle_to_thumbs_rotation,
    cradle_closed,
)

Builder.load_file(join(dirname(__file__), 'capture_screen.kv'))


class CaptureScreen(TooltipScreen, Screen):

    scribe_widget = ObjectProperty(None)
    screen_manager = ObjectProperty(None)
    book_menu_bar = ObjectProperty()
    spread_slider_bar = ObjectProperty()
    capture_spread_box = ObjectProperty(None, allownone=True)
    reopen_at = NumericProperty(None)
    global_time_open = NumericProperty(None)

    _current_marker_key = StringProperty(PT_FOLDOUT)

    __events__ = ('on_book_reset', 'on_start_new_book', 'on_edit_metadata')

    def __init__(self, **kwargs):
        super(CaptureScreen, self).__init__(**kwargs)
        self.book_dir = None
        self.camera_status = {'left': None, 'right': None, 'foldout': None}
        self.cameras_count = 0
        self.page_data = None
        self.page_nums = None
        self.downloaded_book = False
        self.global_time_open = 0
        self.scandata = None
        self.config = None
        self.action_detector = \
            CaptureActionDetector(scribe_globals.CAPTURE_ACTION_BINDINGS)
        self.action_handler = CaptureActionHandler(self)
        self.target_isbn = None

        self.target_extra = None
        self.time_open = None
        self.book_logger = None
        self._autoshoot_running = False
        self._safe_for_autoshoot = True
        self._capture_actions_enabled = False
        self._book_export = None
        self._ia_session = None
        self._page_type_form_popup = popup = \
            self.create_popup(popup_cls=PageTypeFormPopup)
        popup.fbind('on_submit', self._on_page_form_popup_submit)
        self._reshoot_methods = {
            'capture_spread': self.reshoot_spread,
            'capture_cover': self.reshoot_cover,
            'reshoot_spread': self.reshoot_spread,
            'reshoot_cover': self.reshoot_cover,
            'reshoot_cover_foldout': self.reshoot_cover_foldout,
            'capture_foldout': self.capture_foldout
        }
        self.fbind('_current_marker_key',
                   Clock.create_trigger(self._on_current_marker_key, -1))

    def get_ia_session(self):
        if not self._ia_session:
            self._ia_session = btserver.get_ia_session()
        return self._ia_session

    def on_spread_slider_bar(self, screen, bar):
        bar.bind(
            on_option_select=self.on_spread_slider_bar_option_select,
            on_slider_value_up=self.on_spread_slider_bar_value_up,
            autoshoot_state=self.on_spread_slider_autoshoot_state,
            slider_value=self._update_spread_slider_tooltip,
            slider_min=self._update_spread_slider_tooltip,
            slider_max=self._update_spread_slider_tooltip,
            contact_switch_toggle_state=self.on_spread_slider_contact_switch_toggle_state,
        )
        # TODO: Find better way to bind/unbind keyboard
        autoshoot_input = bar.ids.autoshoot_input
        autoshoot_input.bind(focus=self._on_autoshoot_input_focus)

    def on_spread_slider_bar_value_up(self, bar, value):
        self.show_spread(value)
        if self.capture_spread_box:
            self._update_spread_menu_bar_page_type()

    def on_spread_slider_autoshoot_state(self, bar, state):
        if state == 'down':
            self.start_autoshoot_capture()
        elif state == 'normal':
            self.stop_autoshoot_capture()

    def on_spread_slider_contact_switch_toggle_state(self, bar, state):
        pass

    def _update_spread_slider_tooltip(self, bar, *args):
        scandata = self.scandata
        if self.cameras_count == 1:
            if scandata:
                data = scandata.get_page_num(bar.slider_value)
                asserted = self._get_page_number(data)
                asserted = '-' if asserted is None else asserted
            else:
                asserted = '-'
            tooltip = ('Leaf {}/{} | Page {}'.format(int(bar.slider_value),
                                             int(bar.slider_max), asserted))
            bar.slider_tooltip = tooltip
            return
        sides = self.get_displayed_sides()
        right_side = sides['right']
        left_side = sides.get('left', right_side - 1)
        temp = ['Spread {}/{}'.format(int(bar.slider_value), int(bar.slider_max)),
                'Leaves {},{}'.format(left_side, right_side)]
        if scandata:
            data = scandata.get_page_num(right_side)
            a_right = self._get_page_number(data)
            a_right = '-' if a_right is None else a_right
            data = scandata.get_page_num(left_side)
            a_left = self._get_page_number(data)
            a_left = '-' if a_left is None else a_left
            temp.append('Pages {}.{}'.format(a_left, a_right))
        else:
            temp.append('-, -')
        bar.slider_tooltip = ' | '.join(temp)

    def _get_page_number(self, page_number_data):
        # TODO: Remove this method when scandata structure becomes the same
        # for reshooting mode and otherwise
        if page_number_data:
            if isinstance(page_number_data, dict):
                return page_number_data.get('num', None)
            elif isinstance(page_number_data, str):
                return int(page_number_data)
        return None

    def on_scandata_leafs(self, scandata, report):
        if self._current_marker_key in report:
            self.update_spread_slider_markers()

    def update_spread_slider_markers(self, *args):
        scandata = self.scandata
        marker_key = self._current_marker_key
        self.book_menu_bar.use_foldout_buttons = scandata.has_leafs(marker_key)
        spreads = scandata.iter_leafs(marker_key)
        if self.cameras_count != 1:
            new_spread = set()
            for leaf in spreads:
                new_spread.add(leaf // 2)
            spreads = new_spread
        self.spread_slider_bar.set_slider_markers(spreads,
                                                  marker_key.capitalize())
        Logger.info(u'CaptureScreen: Displaying markers with key "{}" '
                    u'in spread slider bar'.format(marker_key))

    def is_autoshoot_capture_running(self):
        return self._autoshoot_running

    def start_autoshoot_capture(self, *args):
        if not self._autoshoot_running:
            self._autoshoot_running = True
            self._safe_for_autoshoot = True
            Clock.unschedule(self.auto_capture_spread)
            shooting_interval = self.spread_slider_bar.autoshoot_value
            Clock.schedule_interval(
                self.auto_capture_spread,
                shooting_interval
            )
            self.spread_slider_bar.autoshoot_state = 'down'
            Logger.info('CaptureScreen: Autoshoot started')

    def stop_autoshoot_capture(self, *args):
        if self._autoshoot_running:
            self._autoshoot_running = False
            self._safe_for_autoshoot = False
            Clock.unschedule(self.auto_capture_spread)
            self.spread_slider_bar.autoshoot_state = 'normal'
            Logger.info('CaptureScreen: Autoshoot stopped')

    def auto_capture_spread(self, *args):
        if self.spread_slider_bar.contact_switch_toggle_state == 'down':
            self._safe_for_autoshoot = True
            self.capture_button()
            self._safe_for_autoshoot = False
            return
        if self._safe_for_autoshoot:
            self.capture_button()
            self._safe_for_autoshoot = False

    def enable_capture_actions(self, *args):
        if not self._capture_actions_enabled:
            Window.bind(on_key_down=self.on_key_down)
            Window.bind(on_key_up=self.on_key_up)
            self.action_detector.reset()
            self.action_detector.bind(on_action=self.action_handler.on_action)
            self._capture_actions_enabled = True
            Logger.debug('CaptureScreen: Enabled keyboard capture actions')

    def disable_capture_actions(self, *args):
        if self._capture_actions_enabled:
            Window.unbind(on_key_down=self.on_key_down)
            Window.unbind(on_key_up=self.on_key_up)
            self.action_detector.unbind(
                on_action=self.action_handler.on_action
            )
            self._capture_actions_enabled = False
            Logger.debug('CaptureScreen: Disabled keyboard capture actions')

    def on_key_down(self, window, keycode, scancode=None, codepoint=None,
                    modifiers=None, **kwargs):
        # TODO: All keyboard actions should be disabled if widget is disabled
        if self.disabled:
            return False
        elif self._capture_actions_enabled:
            if self.action_detector.on_key_down(keycode, scancode, codepoint,
                                                modifiers, **kwargs):
                return True

    def on_key_up(self, window, keycode, scancode=None, codepoint=None,
                  modifiers=None, **kwargs):
        # TODO: All keyboard actions should be disabled if widget is disabled
        if self.disabled:
            return False
        if self._capture_actions_enabled:
            if self.action_detector.on_key_up(keycode, scancode, codepoint,
                                              modifiers, **kwargs):
                return True

    def on_spread_slider_bar_option_select(self, bar, option):
        if option == 'capture_spread':
            self.capture_button()

    def _on_autoshoot_input_focus(self, autoshoot_input, focus):
        if focus:
            self.disable_capture_actions()
        else:
            self.enable_capture_actions()

    def _update_spread_menu_bar_page_type(self, *args):
        sides = self.get_displayed_sides()
        for side, leaf_number in sides.items():
            leaf_data = self.scandata.get_page_data(leaf_number)
            button = self.get_page_type_button(side)
            button.text = leaf_data.get('pageType', PT_NORMAL)

    def abort_shooting(self):
        popup = QuestionPopup(
            title='Configuration error',
            message=('The configuration is incorrect or incomplete.\n'
                     'Please check your metadata.'),
            text_yes='Edit metadata',
            text_no='Close'
        )
        popup.bind(on_submit=self._on_about_shooting_popup_submit)
        popup.open()
        self.screen_manager.transition.direction = 'left'
        self.screen_manager.current = 'upload_screen'

    def _on_about_shooting_popup_submit(self, popup, option):
        if option == popup.OPTION_YES:
            self.screen_manager.transition.direction = 'down'
            self.screen_manager.current = 'metadata_screen'

    def on_pre_leave(self, *args):
        self.stop_autoshoot_capture()
        self.disable_capture_actions()
        super(CaptureScreen, self).on_pre_leave(*args)

    def on_leave(self, *args):
        self._update_timelog()
        self.disable_capture_actions()
        self._push_book_update_event_to_server()
        if self.book:
            #self.book.reload_scandata()
            reload_scandata_task = BookTask(book=self.book,
                                            command='reload_scandata')
            self.scribe_widget.task_scheduler.schedule(reload_scandata_task)
        self.book_dir = None
        self.book = None
        self.scandata = None
        self.config = None
        self.target_isbn = None

        self.target_extra = None
        Logger.info('CaptureScreen: End of scanning session at '
                    '{:%Y-%m-%d%H:%M:%S}'.format(datetime.datetime.now()))
        Logger.info('~' * 90)
        self._teardown_logger()
        self.disable_capture_actions()
        super(CaptureScreen, self).on_leave(*args)

    def _update_timelog(self):
        Logger.debug('CaptureScreen: GTO is {:.2f}s'
                     .format(self.global_time_open))
        time_session = self._get_capture_session_time() or 0
        if self.global_time_open:
            self.global_time_open += time_session
            Logger.debug('CaptureScreen: GTO2 is {:.2f}s'
                         .format(self.global_time_open))
        else:
            self.global_time_open = time_session
            Logger.debug('No time-tracking info for this book. Adding this '
                         'session time of {:.2f}s'.format(time_session))

        if os.path.exists(self.book_dir):
            timelog_filename = join(self.book_dir, 'time.log')
            with open(timelog_filename, 'w+') as fp:
                fp.write(str('{:.2f}'.format(self.global_time_open)))
                Logger.debug('CaptureScreen: Writing {:.2f} to file {}'
                             .format(self.global_time_open, timelog_filename))

    def _get_capture_session_time(self):
        if self.time_open is None:
            return None
        delta = (datetime.datetime.now() - self.time_open)
        return delta.total_seconds()

    def _read_identifier(self):
        identifier = None
        if self.book_dir:
            id_file = join(self.book_dir, 'identifier.txt')
            if not os.path.exists(id_file):
                return identifier
            try:
                identifier = open(id_file).read().strip()
                Logger.debug('CaptureScreen: Read identifier {} from {}'
                             .format(identifier, id_file))
            except Exception:
                Logger.exception('CaptureScreen: Failed to read identifier '
                                 'from {}'.format(id_file))
                identifier = None
        return identifier

    def _push_book_update_event_to_server(self):
        Logger.info('CaptureScreen: Saving to iabdash')
        identifier = self._read_identifier()
        leafs_count = self.scandata.count_pages() if self.scandata else 0
        time_session = self._get_capture_session_time()
        if identifier and time_session is not None and leafs_count:
            payload = {'activeTime': self.global_time_open,
                       'sessionTime': time_session,
                       'numLeaf': leafs_count}
            try:
                push_event('tts-book-update', payload, 'book', identifier,
                           join(self.book_dir, 'iabdash.log'))
                Logger.info('CaptureScreen: Pushed event tts-book-update to '
                            'iabdash with payload: {}'.format(payload))
            except Exception:
                Logger.exception('CaptureScreen: Failed to push '
                                 'tts-book-update event with payload: {}'
                                 .format(payload))

    def _push_book_open_event_to_server(self):
        identifier = self._read_identifier()
        if not (identifier and self.scandata):
            return
        payload = {'id': identifier,
                   'leafNum': self.scandata.count_pages()}
        try:
            push_event('tts-book-open', payload, 'book', identifier,
                       save_data_path=join(self.book_dir, 'iabdash.log'))
            Logger.info('CaptureScreen: Pushed event tts-book-open to iabdash '
                        'with payload: {}'.format(payload))
        except Exception:
            Logger.exception('CaptureScreen: Failed to push tts-book-open '
                             'event with payload: {}'.format(payload))

    def _setup_logger(self):
        try:
            self.book_logger = \
                setup_logger('scanning.log', self.book_dir, Logger)
        except Exception as e:
            Logger.warn('CaptureScreen: Failed to setup book logger.'
                        'Exception: {}'.format(e))

    def _teardown_logger(self):
        try:
            teardown_logger(self.book_logger, Logger)
        except Exception as e:
            Logger.warn('CaptureScreen: Failed to teardown logger.'
                        'Exception: {}'.format(e))
        self.book_logger = None

    def _state_transition(self, commands):
        try:
            for command in commands:
                a = getattr(self.book, command)
                a()
            return True
        except Exception as e:
            popup = InfoPopup(
                title='Error',
                message=str(e),
                auto_dismiss=False
            )
            popup.bind(on_submit=popup.dismiss)
            popup.open()
            return False

    def _raise_book_loading_error(self):
        message = 'This item no longer appears to exist or is not available.\n' \
                  'Click Ok to return to the library list.'
        popup = self.create_popup(popup_cls=InfoPopup,
                                  title='Error opening book',
                                    message=message,)
        popup.bind(on_submit=self._close_widget)
        popup.open()

    def _close_widget(self,  popup, option):
        popup.dismiss()
        self.screen_manager.current = 'upload_screen'

    def on_pre_enter(self, *args):
        target_extra = self.target_extra
        if target_extra:
            self.book_dir = self.target_extra.get('book_dir', self.book_dir)
        if not self.book_dir:
            self._raise_book_loading_error()
            return

        Logger.info('CaptureScreen: on_pre_enter, book_dir is "{}"'
                    .format(self.book_dir))
        self.books_db = self.scribe_widget.books_db
        self.book = self.scribe_widget.books_db.get_item(basename(self.book_dir))
        if not self.book:
            self._raise_book_loading_error()
            return
        self.config = Scribe3Configuration()

        self.downloaded_book = self.book_menu_bar.downloaded_book = False
        # If we re-entered a book after a camera calibration issue, we may have
        # stale images in the cache
        Cache.remove('kv.image')
        Cache.remove('kv.texture')
        upload_widget = self.scribe_widget.ids._upload_widget
        Logger.info('CaptureScreen: Configuration ok: {}'
                    .format(str(upload_widget.configuration_ok)))
        # If metadata is not set correctly, abort
        if not upload_widget.configuration_ok:
            self.abort_shooting()
            return
        self.cameras_count = self.scribe_widget.cameras.get_num_cameras()
        self.scandata = scandata = ScanData(
            self.book_dir,
            downloaded=self.downloaded_book,
        )
        scandata.bind(on_leafs=self.on_scandata_leafs)
        self._push_book_open_event_to_server()
        self.time_open = datetime.datetime.now()
        # check if there is a time-tracking file, and if so load its value
        self.global_time_open = self.get_time_tracking()
        if self.capture_spread_box is None:
            self.show_spread_widget()
        if self.book_dir and os.path.exists(join(self.book_dir, 'downloaded')):
            self.downloaded_book = True
            self.book_menu_bar.downloaded_book = True
            Logger.info('CaptureScreen: Downloaded book: {}'
                        .format(self.book_dir))

        should_capture_cover = False
        if self.book_dir is None or scandata.count_pages() < 2:
            should_capture_cover = True
        else:
            self._setup_logger()
            Logger.info('~' * 90)
            Logger.info(
                'CaptureScreen: '
                'Initialized book scanning session at {:%Y-%m-%d %H:%M:%S}\n'
                'So far, this book has been scanned for {} seconds. | '
                'Scanning with {} cameras'
                    .format(datetime.datetime.now(),
                            self.global_time_open,
                            self.cameras_count)
            )
            if self.downloaded_book and scandata.count_pages() < 2:
                should_capture_cover = True
        has_single_camera = self.cameras_count == 1
        slider_min_value = 1
        slider_max_value = max(slider_min_value,
                               scandata.get_max_leaf_number() or 0)
        if not has_single_camera:
            slider_max_value = int((scandata.get_max_leaf_number() or 0) * 0.5)
            slider_min_value = 0
        if slider_min_value > slider_max_value:
            slider_max_value = slider_min_value
        slider_value = slider_max_value
        if self.downloaded_book:
            foldout_leaf_number = next(scandata.iter_leafs(PT_FOLDOUT), None)
            if foldout_leaf_number is not None:
                slider_value = foldout_leaf_number
                if not has_single_camera:
                    slider_value = int(foldout_leaf_number * 0.5)
                slider_value = max(slider_value, slider_min_value)
        if target_extra:
            target_value = target_extra.get('slider_value', slider_value)
            slider_value = min(max(target_value, slider_min_value),
                               slider_max_value)
        self.spread_slider_bar.slider_min = slider_min_value
        self.spread_slider_bar.slider_max = slider_max_value
        self.spread_slider_bar.slider_value = slider_value
        self.update_spread_slider_markers()
        self.show_spread(slider_value)
        self.spread_slider_bar.scan_button_disabled = False
        self.spread_slider_bar.contact_switch_present = self.config.get('contact_switch', None) is not None
        self._update_book_menu_bar()
        self.enable_capture_actions()
        if should_capture_cover:
            for side in self.get_displayed_sides():
                self.set_page_widget(side, scribe_globals.LOADING_IMAGE)
            if not self.scribe_widget.cameras.are_calibrated():
                extra = {'should_show_capture_cover_popup': True}
                self.show_calibration_popup(extra=extra)
                return
            self.show_capture_cover_popup()
        if not (should_capture_cover or has_single_camera) and self.book_dir \
                and os.path.exists(join(self.book_dir, 'preloaded')):
            md = get_metadata(self.book_dir)
            if md.get('source', None) == 'folio':
                self.show_folio_warning_popup()
        super(CaptureScreen, self).on_pre_enter(*args)

    def on_enter(self, *args):
        extra = self.target_extra
        if extra and self.capture_spread_box:
            if extra.get('should_enable_foldout_mode', False) \
                    and self.cameras_count == 3:
                self.capture_spread_box.enable_foldout_mode()
        super(CaptureScreen, self).on_enter(*args)

    def show_capture_cover_popup(self):
        self.disable_capture_actions()
        popup = self.create_popup(
            popup_cls=InfoPopup,
            auto_dismiss=False,
            **self._create_capture_cover_popup_attrs()
        )
        popup.bind(on_submit=self._on_capture_cover_popup_submit)
        popup.open()

    def _create_capture_cover_popup_attrs(self):
        if self.cameras_count == 1:
            return {
                'title': 'Begin a new folio scan',
                'message': 'Place the COLOR CARD\non the scanning surface.',
                'text_ok': 'Shoot Color Card'
            }
        return {
            'title': 'Prepare First Spread',
            'message': ('Prepare the book to capture the first spread.\n\n'
                        'Generally, it consists of a Color Card on the '
                        'left,\nand the Front Cover on the right.'),
            'text_ok': 'Shoot Cover'
        }

    def _on_capture_cover_popup_submit(self, popup, option):
        popup.dismiss()
        self.capture_cover()

    def show_folio_warning_popup(self, *args):
        message = 'This item is designated as a ' \
                  'folio, usually for use at a Foldout Station and charged ' \
                  'at a higher rate than a regular, scribe item.\n\n' \
                  'Do you want to continue?\n\nPlease consult your ' \
                  'Cataloger or Manager if you are unsure.'
        popup = self.create_popup(
            popup_cls=QuestionPopup,
            message=message,
            title='Folio Item Detected',
            text_no='Cancel',
            auto_dismiss=False
        )
        popup.height = '290dp'
        popup.bind(on_submit=self.on_show_folio_warning_popup_submit)
        popup.open()

    def on_show_folio_warning_popup_submit(self, popup, option):
        if option == popup.OPTION_YES:
            popup.dismiss()
            Logger.info('CaptureScreen: Continuing capture of folio book with '
                        '{} cameras'.format(self.cameras_count))
        elif option == popup.OPTION_NO:
            repub_state = '-1'
            try:
                self.set_book_repub_state(repub_state)
            except Exception:
                identifier = read_book_identifier(self.book_dir)
                Logger.error('CaptureScreen: Failed to set repub_state '
                             'to {} for item with identifier {}'
                             .format(repub_state, identifier))
            popup.dismiss(animation=False)
            self.screen_manager.current = 'upload_screen'



    def set_book_repub_state(self, state):
        Logger.info('CaptureScreen: Setting repub_state to {}'.format(state))
        identifier = read_book_identifier(self.book_dir)
        ia_session = self.get_ia_session()
        ia_item = ia_session.get_item(identifier)
        response = ia_item.modify_metadata({'repub_state': state})
        Logger.info('CaptureScreen: Response from cluster: {} | '
                    'Headers {}'.format(response.text, response.headers))

    def _update_book_menu_bar(self, *args):
        menu = self.book_menu_bar
        book_dir = self.book_dir
        menu_identifier = self._read_identifier() or u''
        get = get_string_value_if_list
        if book_dir:
            md = get_metadata(book_dir)
            title = get(md, 'title') or u'NULL'
            creator = get(md, 'creator') or get(md, 'author') or u'NULL'
            language = get(md, 'language') or u'NULL'
            menu_title = u'{}, {} ({})'.format(title, creator, language)
        else:
            menu_title = u''
        menu.identifier = menu_identifier
        menu.title = menu_title
        next = PT_FOLDOUT if self._current_marker_key == KEY_NOTE else KEY_NOTE
        menu.next_marker_key = next
        menu.current_marker_key = self._current_marker_key

    def on_book_menu_bar(self, screen, bar):
        bar.bind(on_option_select=self.on_book_menu_bar_option_select)

    def on_book_menu_bar_option_select(self, bar, option):
        if option == 'edit':
            self.show_book_metadata_screen()
        elif option == 'delete':
            self.show_delete_book_popup()
        elif option == 'export':
            self.start_book_export()
        elif option == 'notes':
            self.show_notes_popup()
        elif option == 'internal_notes':
            self.show_internal_notes_popup()
        elif option == 'upload':
            self.show_upload_book_popup_and_leave()
        elif option == 'upload_and_new_book':
            self.show_upload_book_popup_and_start_new_book()
        elif option == 'page_type':
            self.switch_markers_in_spread_slider()
        elif option == 'previous_foldout':
            self.show_previous_marked_spread()
        elif option == 'next_foldout':
            self.show_next_marked_spread()
        elif option == 'send_to_station':
            self.show_send_to_station_popup()
        elif option == 'reset':
            if not self.downloaded_book:
                self.show_reset_book_popup()

    def show_book_metadata_screen(self):
        self.dispatch('on_edit_metadata')

    def show_send_to_station_popup(self, *args):
        self.action = SendToStationActionMixin(
            book=self.book,
            on_popup_open=self._on_popup_open,
            on_popup_dismiss=self._on_popup_dismiss,
        )
        self.action.display()

    def switch_markers_in_spread_slider(self):
        if self.scandata:
            current = self._current_marker_key
            if current == PT_FOLDOUT:
                current = KEY_NOTE
                old = PT_FOLDOUT
            else:
                current = PT_FOLDOUT
                old = KEY_NOTE
            self._current_marker_key = current

    def _on_current_marker_key(self, *args):
        current = self._current_marker_key
        old = KEY_NOTE if current == PT_FOLDOUT else PT_FOLDOUT
        self.book_menu_bar.current_marker_key = current
        self.book_menu_bar.next_marker_key = old
        self.update_spread_slider_markers()

    def has_foldout_target_selected(self):
        path = join(self.book_dir, 'send_to_station')
        return os.path.exists(path)

    def show_previous_marked_spread(self, *args):
        bar = self.spread_slider_bar
        if bar.slider_value == bar.slider_min:
            return
        sides = self.get_displayed_sides()
        has_single_camera = self.cameras_count == 1
        leaf_number = sides['foldout'] if has_single_camera else sides['left']
        marker_key = self._current_marker_key
        spread_number = \
            self.scandata.get_previous_leaf(leaf_number, marker_key)
        if spread_number is not None:
            if not has_single_camera:
                spread_number /= 2
            self.show_spread(spread_number)

    def show_next_marked_spread(self, *args):
        bar = self.spread_slider_bar
        if bar.slider_value == bar.slider_max:
            return
        sides = self.get_displayed_sides()
        has_single_camera = self.cameras_count == 1
        leaf_number = sides['foldout'] if has_single_camera else sides['right']
        marker_key = self._current_marker_key
        spread_number = self.scandata.get_next_leaf(leaf_number, marker_key)
        if spread_number is not None:
            if not has_single_camera:
                spread_number /= 2
            self.show_spread(spread_number)

    def show_reset_book_popup(self, *args):
        self.action = ResetBookActionMixin(
            book=self.book,
            task_scheduler=self.scribe_widget.task_scheduler,
            done_task_callback=self.book_reset_callback,
            on_popup_open=self._on_popup_open,
            on_popup_dismiss=self._on_popup_dismiss,
        )
        self.action.display()

    def book_reset_callback(self, book, task, *args):
        self.action = None
        if not task.error:
            self.dispatch('on_book_reset')

    def show_delete_book_popup(self, *args):
        self.action = DeleteBookActionMixin(
            book=self.book,
            task_scheduler=self.scribe_widget.task_scheduler,
            done_action_callback=self._done_delete_callback,
            on_popup_open=self._on_popup_open,
            on_popup_dismiss=self._on_popup_dismiss,
        )
        self.action.display()

    def _done_delete_callback(self, book, task, popup, *args):
        self.action = None
        self.screen_manager.current = 'upload_screen'

    def start_book_export(self, *args):
        self.disable_capture_actions()
        self._book_export = export = BookExport(self.book_dir)
        export.bind(on_finish=self.on_book_export_finish)
        export.start()

    def on_book_export_finish(self, *args):
        self._book_export = None
        self.enable_capture_actions()

    def show_internal_notes_popup(self, *args):
        scandata = self.scandata
        internal_notes = scandata.get_internal_book_notes() or ''
        popup = self.create_popup(popup_cls=BookNotesPopup,
                                  notes=internal_notes,
                                  title='Edit internal book notes')
        popup.bind(on_submit=self.on_internal_book_notes_submit)
        popup.open()

    def on_internal_book_notes_submit(self, popup, notes):
        scandata = self.scandata
        internal_notes = scandata.get_internal_book_notes() or ''
        notes = notes.strip()
        if internal_notes != notes:
            scandata.set_internal_book_notes(notes)
            scandata.save()
            if notes:
                message = 'Saved internal book notes: %s' \
                          % ('\n%s' % notes if '\n' in notes else notes)
            else:
                message = 'Removed internal book notes'
            Logger.info('CaptureScreen: %s' % message)

    def show_notes_popup(self, *args):
        metadata = get_metadata(self.book_dir)
        notes = metadata.get('notes', None) or ''
        popup = self.create_popup(popup_cls=BookNotesPopup,
                                  notes=notes,
                                  title='Edit public book notes')
        popup.bind(on_submit=self.on_book_notes_submit)
        popup.open()

    def on_book_notes_submit(self, popup, notes):
        metadata = get_metadata(self.book_dir)
        metadata_notes = metadata.get('notes', None) or ''
        notes = notes.strip()
        if metadata_notes != notes:
            if notes:
                metadata['notes'] = notes
                set_metadata(metadata, self.book_dir)
                message = 'Saved public book notes: %s' \
                          % ('\n%s' % notes if '\n' in notes else notes)
            else:
                metadata.pop('notes', None)
                set_metadata(metadata, self.book_dir)
                message = 'Removed public book notes'
            Logger.info('CaptureScreen: %s' % message)

    def show_upload_book_popup_and_start_new_book(self, *args):
        extra = {'should_start_new_book': True}
        self._show_upload_book_popup(extra)

    def show_upload_book_popup_and_leave(self):
        extra = {'should_leave': True}
        self._show_upload_book_popup(extra)

    def _show_upload_book_popup(self, extra):
        self.action = UploadBookWrapper(
            book=self.book,
            task_scheduler=self.scribe_widget.task_scheduler,
            on_popup_open=self._on_popup_open,
            on_popup_dismiss=self._on_popup_dismiss,
            done_action_callback=self._upload_book_action_callback,
            extra=extra,
            show_send_to_station=self.show_send_to_station_popup
        )
        self.action.display()

    def _upload_book_action_callback(self, book, task, popup, *args, **kwargs):
        self.action = None
        if type(popup) == ThreeOptionsQuestionPopup:
            return
        extra = popup.extra
        if extra.get('should_leave', False):
            Logger.info('CaptureScreen: Leaving capture screen')
            self.screen_manager.current = 'upload_screen'
        elif extra.get('should_start_new_book', False):
            Logger.info('CaptureScreen: Starting new book')
            self.dispatch('on_start_new_book')

    def flag_book_for_upload(self):
        if self.book.is_downloaded():
            if self.book.get_numeric_status() == UploadStatus.corrections_in_progress.value:
                return self._state_transition(['do_queue_upload_corrections'])
            elif self.book.get_numeric_status() == UploadStatus.foldouts_in_progress.value:
                return self._state_transition(['do_queue_upload_foldouts'])
        else:
            return self._state_transition(['do_queue_processing'])

    def check_for_missing_images(self):
        book_path = self.book_dir
        scandata = self.scandata
        if not (book_path and scandata):
            return 'Cover image is missing!'
        max_leaf_number = scandata.get_max_leaf_number()
        if max_leaf_number is None or max_leaf_number < 1:
            return 'Cover image is missing'
        for leaf_number in range(max_leaf_number + 1):
            leaf_data = scandata.get_page_data(leaf_number)
            image_path = join(book_path, '{:04d}.jpg'.format(leaf_number))
            if not (leaf_data and os.path.exists(image_path)):
                if leaf_number == 0 or leaf_number == 1:
                    return 'Cover image is missing!'
                return 'Image #{} is missing'.format(leaf_number)
        '''
        if max_leaf_number % 2 == 0:
            if self.cameras_count == 1:
                Logger.info('queue_upload: Allowing upload of an odd number '
                            'of leafs because single-camera mode was detected')
            else:
                return 'Image #{} is missing!'.format(max_leaf_number + 1)
        '''
        return None

    def set_time_tracking(self):
        delta_time = (datetime.datetime.now() - self.time_open)
        time_session = delta_time.total_seconds()
        if self.global_time_open:
            self.global_time_open += time_session
        else:
            Logger.debug('CaptureScreen: No time-tracking info for this book. '
                         'Adding this session...')
            self.global_time_open = time_session
        timelog_filename = join(self.book_dir, 'time.log')
        with open(timelog_filename, 'w+') as fp:
            Logger.debug('CaptureScreen: Now writing time tracking info to {}'
                         .format(timelog_filename))
            fp.write(str('{:.2f}'.format(self.global_time_open)))
        return self.global_time_open

    def get_time_tracking(self):
        # Check if there is a time-tracking file, and if so load its value
        global_time_open = 0
        if self.book_dir:
            filename = join(self.book_dir, 'time.log')
            if os.path.exists(filename):
                Logger.debug('CaptureScreen: Time-tracking file found at {}'
                             .format(filename))
                try:
                    with open(filename, 'r') as fp:
                        global_time_open = float(fp.readline())
                        Logger.debug('CaptureScreen: Found time tracking value of {:.2f}s'
                                     .format(global_time_open))
                except Exception:
                    Logger.exception('CaptureScreen: Failed to read time tracking value '
                                     'from {}'.format(filename))
            else:
                Logger.debug('CaptureScreen: Time-tracking file not found at {}'
                             .format(filename))
        else:
            Logger.warning('CaptureScreen: No time-tracking file found. Initializing to 0')

        return global_time_open

    def show_calibration_popup(self, extra=None):
        popup = self.create_popup(popup_cls=CalibrateCamerasPopup, extra=extra)
        popup.bind(on_submit=self.on_calibration_popup_submit)
        popup.open()

    def on_calibration_popup_submit(self, popup, option):
        if option == popup.OPTION_GOTO_CALIBRATION:
            extra = self.create_state()
            if popup.extra:
                extra.update(popup.extra)
            self.goto_calibration(extra=extra)
        elif option == popup.OPTION_CONTINUE:
            self.scribe_widget.cameras.set_calibrated()
            extra = popup.extra
            if extra:
                if extra.get('should_capture_button', False):
                    self.capture_button()
                elif extra.get('should_show_capture_cover_popup', False):
                    self.show_capture_cover_popup()
                elif extra.get('should_enable_foldout_mode', False):
                    side = extra.get('side', None)
                    if side:
                        self.capture_foldout(side)
                elif extra.get('should_reshoot_cover', False):
                    self.reshoot_cover(None)
                elif extra.get('should_reshoot_cover_foldout', False):
                    self.reshoot_cover_foldout(None)
                elif extra.get('should_capture_spread', False):
                    self.capture_spread()
                elif extra.get('should_reshoot_spread', False):
                    self.reshoot_spread()

    def capture_cover(self):
        self._setup_logger()
        Logger.info('~' * 90)
        Logger.info('CaptureWidget: New book created at '
                    '{:%Y-%m-%d %H:%M:%S}\n'
                    'So far, this book has been scanned for {} seconds. |'
                    'Now scanning with {} cameras'
                    .format(datetime.datetime.now(),
                            self.global_time_open,
                            self.cameras_count))
        Logger.debug('CaptureScreen: Book directory: "{}"'
                     .format(self.book_dir))
        if self.cameras_count == 1:
            md = get_metadata(self.book_dir)
            md['source'] = 'folio'
            set_metadata(md, self.book_dir)
        # Init scandata, now that book_dir is set
        self.scandata = ScanData(
            self.book_dir,
            downloaded=self.downloaded_book,
        )
        self.spread_slider_bar.scan_button_disabled = True
        for side in self.camera_status:
            self.camera_status[side] = None
        scandata = self.scandata
        left_side = self.adjust_side('left')
        right_side = self.adjust_side('right')
        has_single_camera = self.cameras_count == 1
        if not has_single_camera:
            leaf_number = 0
            kwargs = self.create_camera_kwargs(left_side, leaf_number,
                                               capture_method='capture_cover')
            queue = self.get_capture_queue(left_side)
            queue.put(kwargs)
            scandata.insert(leaf_number, left_side, page_type=PT_COLOR_CARD)
            scandata.set_ppi(leaf_number, self.get_leaf_ppi(leaf_number))
            scandata.set_capture_time(leaf_number, None)
            leaf_number = 1
            self.set_page_widget('right', scribe_globals.LOADING_IMAGE)
            kwargs = self.create_camera_kwargs(right_side, leaf_number,
                                               capture_method='capture_cover')
            queue = self.get_capture_queue(right_side)
            queue.put(kwargs)
            page_type = PT_COVER
            scandata.insert(leaf_number, right_side, page_type)
            self.set_page_type_button(right_side, page_type)
            scandata.set_ppi(leaf_number, self.get_leaf_ppi(leaf_number))
            scandata.set_capture_time(leaf_number, None)
        else:
            leaf_number = 0
            path, thumb_path = self.get_paths(leaf_number)
            shutil.copy(scribe_globals.FAKE_IMAGE, path)
            shutil.copy(scribe_globals.FAKE_IMAGE, thumb_path)
            scandata.insert(leaf_number, left_side, page_type='Delete')
            scandata.set_ppi(leaf_number, self.get_leaf_ppi(leaf_number))
            scandata.set_capture_time(leaf_number, None)
            leaf_number = 1
            self.set_page_widget(right_side, scribe_globals.LOADING_IMAGE)
            queue = self.get_capture_queue(right_side)
            kwargs = self.create_camera_kwargs(right_side, leaf_number,
                                               capture_method='capture_cover')
            queue.put(kwargs)
            page_type = PT_COVER
            scandata.insert(leaf_number, right_side, page_type)
            self.set_page_type_button(right_side, page_type)
            scandata.set_ppi(leaf_number, self.get_leaf_ppi(leaf_number))
            scandata.set_capture_time(leaf_number, None)
            rotate_degree = (
                    self.config.get_integer('default_single_camera_rotation', 180) % 360
            )
            scandata.update_rotate_degree(leaf_number, rotate_degree)
            Logger.info('Saved leaf {} with rotation {}'
                        .format(leaf_number, rotate_degree))

        preprocess = {}
        if self.config.get('postprocess_instructions'):
            for param in self.config.get('postprocess_instructions'):
                if self.config.is_true('postprocess_instructions/{}'.format(param)):
                    Logger.info('CaptureScreen: Adding extra preprocessing option '
                                '{} to scandata'.format(param))
                    preprocess[param] = True
        if preprocess:
            scandata.set_bookdata('processInstructions', preprocess)

        scandata.save()
        max_leaf_number = scandata.get_max_leaf_number()
        if self.cameras_count == 1:
            slider_value = max_leaf_number
        else:
            slider_value = int(max_leaf_number / 2.0)
        self.spread_slider_bar.slider_max = slider_value
        self.spread_slider_bar.slider_value = slider_value
        # New scandata is created, so bind to its events
        scandata.bind(on_leafs=self.on_scandata_leafs)
        self.update_spread_slider_markers()

    def reshoot_cover(self, popup=None, *args):
        if popup:
            popup.dismiss()
        bar = self.spread_slider_bar
        if bar.slider_value != bar.slider_min:
            Logger.error('CaptureScreen: Called reshoot_cover while not on '
                         'the cover screen')
            return
        if not self.scribe_widget.cameras.are_calibrated():
            extra = {'should_reshoot_cover': True}
            self.show_calibration_popup(extra=extra)
            return
        # TODO: can we use img.reload() instead?
        Cache.remove('kv.image')
        Cache.remove('kv.texture')
        bar.scan_button_disabled = True
        self.delete_current_spread()
        for side, leaf_number in self.get_displayed_sides().items():
            self.camera_status[side] = None
            self.set_page_widget(side, scribe_globals.LOADING_IMAGE)
            self.scandata.set_capture_time(leaf_number, None)
            kwargs = self.create_camera_kwargs(side, leaf_number,
                                               capture_method='reshoot_cover')
            queue = self.get_capture_queue(side)
            queue.put(kwargs)
        if self.cameras_count == 1:
            page_type = self.get_default_page_type()
            self.scandata.update(1, 'foldout', page_type)
            self.set_page_type_button('foldout', page_type)
            rotate_degree = (
                    self.config.get_integer('default_single_camera_rotation', 180) % 360
            )
            self.scandata.update_rotate_degree(1, rotate_degree)
            Logger.info('Updated leaf {} with rotation {}'
                        .format(1, rotate_degree))
        self.scandata.save()

    def reshoot_cover_foldout(self, popup=None, *args):
        if popup:
            popup.dismiss()
        bar = self.spread_slider_bar
        if bar.slider_value != bar.slider_min:
            Logger.error('CaptureScreen: Called reshoot_cover_foldout while '
                         'not on the cover screen')
            return
        if not self.scribe_widget.cameras.are_calibrated():
            extra = {'should_reshoot_cover_foldout': True}
            self.show_calibration_popup(extra=extra)
            return
        bar.scan_button_disabled = True
        side = self.adjust_side('right')
        self.camera_status[side] = None
        # TODO: can we use img.reload() instead?
        Cache.remove('kv.image')
        Cache.remove('kv.texture')
        self.set_page_widget('foldout', scribe_globals.LOADING_IMAGE)
        self.scandata.set_capture_time(1, None)
        queue = self.get_capture_queue(side)
        kwargs = self.create_camera_kwargs(
            'foldout', 1, capture_method='reshoot_cover_foldout'
        )
        queue.put(kwargs)
        if self.cameras_count == 1:
            rotate_degree = (
                    self.config.get_integer('default_single_camera_rotation', 180) % 360
            )
            self.scandata.update_rotate_degree(1, rotate_degree)
            Logger.info('Updated leaf {} with rotation {}'
                        .format(1, rotate_degree))
        self.scandata.save()

    def reshoot_spread(self, popup=None, *args):
        spread_slider = self.spread_slider_bar
        if spread_slider.slider_value == spread_slider.slider_min:
            self.reshoot_cover(popup)
        else:
            if popup:
                popup.dismiss()
            if not self.scribe_widget.cameras.are_calibrated():
                extra = {'should_reshoot_spread': True}
                self.show_calibration_popup(extra=extra)
                return
            self._reshoot_spread()

    def _reshoot_spread(self):
        if self.spread_slider_bar.scan_button_disabled:
            Logger.error('CaptureScreen: scan_button is disabled, skipping '
                         'this call to capture_spread')
            return
        self.spread_slider_bar.scan_button_disabled = True
        self.delete_current_spread()
        scandata = self.scandata
        sides = self.get_displayed_sides()
        for side, leaf_number in sides.items():
            self.camera_status[side] = None
            self.set_page_widget(side, scribe_globals.LOADING_IMAGE)
            stats = self.get_stats(side)
            stats['capture_time'] = None
            queue = self.get_capture_queue(side)
            kwargs = self.create_camera_kwargs(side, leaf_number,
                                               capture_method='reshoot_spread')
            queue.put(kwargs)
            leaf_data = scandata.get_page_data(leaf_number)
            if not leaf_data:
                scandata.update(leaf_number, side)
                if self.cameras_count == 1:
                    degree = self.config.get_integer('default_single_camera_rotation', 180)
                    degree %= 360
                    scandata.update_rotate_degree(leaf_number, degree)
                    Logger.info('Updated leaf {} with rotation {}'
                                .format(leaf_number, degree))
            else:
                if leaf_data['pageType'] == 'Foldout':
                    degree = self.config.get_integer('default_single_camera_rotation', 180)
                    scandata.update_rotate_degree(leaf_number, degree)
            scandata.set_capture_time(leaf_number, None)
        scandata.save()

    def calibrate_and_capture_spread(self, *args):
        if not self.scribe_widget.cameras.are_calibrated():
            extra = {'should_capture_spread': True}
            self.show_calibration_popup(extra=extra)
            return
        self.capture_spread()

    def capture_spread(self, popup=None):
        if popup:
            popup.dismiss()
        scandata = self.scandata
        if self.spread_slider_bar.scan_button_disabled:
            Logger.error('CaptureScreen: scan_button is disabled, skipping '
                         'this call to capture_spread')
            return
        self.spread_slider_bar.scan_button_disabled = True
        sides = self.get_displayed_sides()
        offset = len(sides)
        for side in sides:
            self.camera_status[side] = None
            # Increase leaf_number by offset as these are target leaf numbers
            sides[side] += offset
        spread_slider = self.spread_slider_bar
        if spread_slider.slider_value != spread_slider.slider_max:
            Logger.info('CaptureScreen: Preparing book for insert')
            # We are inserting a spread, so we need to rename images after
            # the current spread to create a space to place the inserted images
            self.prepare_for_insert()
        page_type = self.get_default_page_type()
        for side, leaf_number in sides.items():
            self.set_page_widget(side, scribe_globals.LOADING_IMAGE)
            stats = self.get_stats(side)
            stats['leaf_num'] = leaf_number
            stats['page_type'] = page_type
            stats['capture_time'] = None
            queue = self.get_capture_queue(side)
            kwargs = self.create_camera_kwargs(side, leaf_number,
                                               capture_method='capture_spread')
            queue.put(kwargs)
            scandata.insert(leaf_number, side, page_type)
            scandata.set_capture_time(leaf_number, None)
            if self.cameras_count == 1:
                rotate_degree = (
                        self.config.get_integer('default_single_camera_rotation', 180) % 360
                )
                scandata.update_rotate_degree(leaf_number, rotate_degree)
                Logger.info('Updated leaf {} with rotation {}'
                            .format(leaf_number, rotate_degree))
            stats['ppi'] = ppi_value = self.get_leaf_ppi(leaf_number)
            self.set_page_ppi_button(side, ppi_value)
        spread_slider.slider_max += 1
        spread_slider.slider_value += 1
        # TODO: We can optimize compute_page_nums() for the capture_spread()
        # case
        max_leaf_number = scandata.get_max_leaf_number()
        Logger.info('CaptureScreen: Computing page numbers with '
                    'end_leaf_number: {}'.format(max_leaf_number))
        scandata.compute_page_nums(max_leaf_number)
        scandata.save()
        for side, leaf_number in sides.items():
            self.set_page_number_button(side, leaf_number)

    def capture_foldout(self, side, *args):
        if not self.scribe_widget.cameras.are_calibrated():
            extra = {'should_enable_foldout_mode': True, 'side': side}
            self.show_calibration_popup(extra=extra)
            return
        # TODO: can we use img.reload() instead?
        Cache.remove('kv.image')
        Cache.remove('kv.texture')
        self.set_page_widget(side, scribe_globals.LOADING_IMAGE)
        self.spread_slider_bar.scan_button_disabled = True
        self.camera_status[side] = None
        sides = self.get_displayed_sides()
        leaf_number = sides[side]
        stats = self.get_stats(side)
        stats['page_type'] = page_type = PT_FOLDOUT
        stats['ppi'] = self.get_leaf_ppi(leaf_number)
        stats['capture_time'] = None
        self.set_page_type_button(side, page_type)
        queue = self.get_capture_queue(side)
        kwargs = self.create_camera_kwargs('foldout', leaf_number,
                                           capture_method='capture_foldout')
        queue.put(kwargs)
        self.scandata.update(leaf_number, 'foldout', page_type=page_type)
        self.scandata.set_capture_time(leaf_number, None)
        if self.cameras_count == 1:
            rotate_degree = (
                    self.config.get_integer('default_single_camera_rotation', 180) % 360
            )
            self.scandata.update_rotate_degree(leaf_number, rotate_degree)
            Logger.info('Saved leaf {} with rotation {}'
                        .format(leaf_number, rotate_degree))
        self.scandata.save()

    def capture_button(self):
        if not self.book_dir:
            Logger.error('CaptureScreen: Called capture_button, but book '
                         'directory is not set')
            return
        if self.spread_slider_bar.contact_switch_toggle_state == 'down' and not cradle_closed():
            if self.spread_slider_bar.autoshoot_state == 'down':
                return
            else:
                self.stop_autoshoot_capture()
                Logger.info('The cradle is not closed')
                popup = self.create_popup(
                    title='Error: cradle is not closed', popup_cls=InfoPopup,
                    auto_dismiss=True,
                    size_hint=(None, None), size=('230dp', '100dp')
                )
                popup.open()
                return
        if not has_free_disk_space(self.book_dir):
            self.stop_autoshoot_capture()
            content = ColorButton(text='OK')
            Logger.info('capture_button: the disk is full!')
            popup = self.create_popup(
                title='Error: the disk is full',
                content=content, auto_dismiss=False,
                size_hint=(None, None), size=('230dp', '100dp')
            )
            content.bind(on_press=popup.dismiss)
            popup.open()
            return
        if not self.scribe_widget.cameras.are_calibrated():
            extra = {'should_capture_button': True}
            self.show_calibration_popup(extra=extra)
            return
        bar = self.spread_slider_bar
        if bar.slider_value == bar.slider_max:
            self.capture_spread()
        else:
            self.stop_autoshoot_capture()
            popup = self.create_popup(popup_cls=ReshootInsertSpreadPopup)
            popup.bind(on_submit=self._on_reshoot_insert_spread_popup_submit)
            popup.open()

    def _on_reshoot_insert_spread_popup_submit(self, popup, option):
        if option == popup.OPTION_RESHOOT:
            self.reshoot_spread()
        elif option == popup.OPTION_INSERT:
            self.capture_spread()

    def prepare_for_insert(self):
        '''We are inserting a spread, so we need to rename images after
        the current spread to create a space to place the inserted images
        '''
        sides = self.get_displayed_sides()
        current = sides.get('left', None)
        if current is None:
            current = sides['foldout']
        offset = len(sides)
        start_page_number = current + offset
        end_page_number = self.get_page_max_value()
        Logger.info('CaptureScreen: Preparing for insert at {}'
                     .format(current))
        for page_number in range(end_page_number, start_page_number - 1, -1):
            old_path, old_thumb = self.get_paths(page_number)
            new_path, new_thumb = self.get_paths(page_number + offset)
            Logger.info('CaptureScreen: Renaming "{}" to "{}"'
                         .format(old_path, new_path))
            try:
                os.rename(old_path, new_path)
            except Exception:
                Logger.exception('CaptureScreen: Failed to rename "{}" to "{}"'
                                 .format(old_path, new_path))
            Logger.info('CaptureScreen: Renaming "{}" to "{}"'
                         .format(old_thumb, new_thumb))
            try:
                os.rename(old_thumb, new_thumb)
            except Exception:
                Logger.exception('CaptureScreen: Failed to rename "{}" to "{}"'
                                 .format(old_thumb, new_thumb))

    def delete_current_spread(self):
        sides = self.get_displayed_sides()
        for side, page_number in sides.items():
            path, thumb_path = self.get_paths(page_number)
            try:
                Logger.debug('CaptureScreen: Deleting page {}'
                             .format(page_number))
                if os.path.exists(path):
                    os.unlink(path)
                    Logger.debug('CaptureScreen: Deleted "{}"'.format(path))
                if os.path.exists(thumb_path):
                    os.unlink(thumb_path)
                    Logger.debug('CaptureScreen: Deleted "{}"'
                                 .format(thumb_path))
            # Do not alter scandata here, since it is called by functions that
            # expect to replace images in-place, like reshoot_cover()
            # self.scandata.delete_spread(left_page_num, right_page_num)
            except Exception:
                Logger.exception('CaptureScreen: Failed to delete page {}'
                                 .format(page_number))
                break
                # self.ids._label.text = 'ERROR! Could not delete spread. '
                #                        'Your book is possibly corrupt!'
                # self.ids._cancel_button.disabled = False
                # return

    def delete_current_spread_and_rename(self):
        sides = self.get_displayed_sides()
        offset = len(sides)
        current_leaf_number = sides.get('left', None)
        if current_leaf_number is None:
            current_leaf_number = sides['foldout']
        next_leaf_number = current_leaf_number + offset - 1
        self.delete_current_spread()
        # Note that range is not inclusive, so we add one to the end
        # TODO: Check if for loop works with CaptureLeaf
        scandata = self.scandata
        max_leaf_number = scandata.get_max_leaf_number()
        next_leaf_number = min(next_leaf_number, max_leaf_number)
        for leaf_number in range(next_leaf_number + 1, max_leaf_number + 1):
            old_path, old_thumb = self.get_paths(leaf_number)
            new_path, new_thumb = self.get_paths(leaf_number - offset)
            Logger.debug('CaptureScreen: Renaming "{}" to "{}"'
                         .format(old_path, new_path))
            try:
                os.rename(old_path, new_path)
            except Exception:
                Logger.exception('CaptureScreen: Failed to rename "{}" to "{}"'
                                 .format(old_path, new_path))
            Logger.debug('CaptureScreen: Renaming "{}" to "{}"'
                         .format(old_thumb, new_thumb))
            try:
                os.rename(old_thumb, new_thumb)
            except Exception:
                Logger.exception('CaptureScreen: Failed to rename "{}" to "{}"'
                                 .format(old_path, new_path))
        scandata.delete_spread(current_leaf_number, next_leaf_number)
        scandata.save()

        min_slider_value = 1 if self.cameras_count == 1 else 0
        max_slider_value = scandata.get_max_leaf_number() or 0
        new_left_leaf_number = current_leaf_number - offset
        if self.cameras_count != 1:
            max_slider_value = int(max_slider_value * 1.0 / offset)
        max_slider_value = max(max_slider_value, min_slider_value)
        slider_value = int(new_left_leaf_number * 1.0 / offset)
        slider_value = max(min_slider_value, slider_value)
        self.spread_slider_bar.slider_max = max_slider_value
        self.spread_slider_bar.slider_value = slider_value
        # Since we have renamed files, we need to get kivy to not use the
        # cached images. However, img_obj.reload() is not working for us. For
        # now, we will remove all cached images.
        Cache.remove('kv.image')
        Cache.remove('kv.texture')
        self.show_spread(slider_value)

    def start_image_export_filechooser(self, source_path):
        self.disable_capture_actions()
        filename = os.path.basename(source_path)
        default_path = join(os.path.expanduser('~'), filename)
        _, ext = os.path.splitext(filename)
        filters = [
                    ['{} image file'.format(ext),
                    '*{}'.format(ext.lower()),
                    '*{}'.format(ext.upper())]
                   ]
        filechooser = FileChooser()
        callback = partial(self.on_image_export_selection, source_path)
        filechooser.bind(on_selection=callback)
        filechooser.bind(on_dismiss=self.enable_capture_actions)
        filechooser.save_file(title='Export image',
                              icon='./images/window_icon.png',
                              filters=filters,
                              path=default_path)

    def on_image_export_selection(self, source_path, chooser, selection):
        if selection:
            destination_path = selection[0]
            root, ext = os.path.splitext(source_path)
            if not destination_path.endswith(ext):
                destination_path += ext
            self.export_image(source_path, destination_path)

    def export_image(self, source, destination):
        error = None
        try:
            shutil.copyfile(source, destination)
            Logger.info('CaptureScreen: Image exported from "{}" to "{}"'
                        .format(source, destination))
        except shutil.Error as error:
            Logger.exception('CaptureScreen: Image source path are the same. '
                             'Source "{}", destination "{}".'
                             .format(source, destination))
        except IOError as error:
            Logger.exception('CaptureScreen: Destination "{}" is not writable'
                             .format(destination))
        except Exception as error:
            Logger.exception('CaptureScreen: Unable to export image from "{}" '
                             'to "{}".'.format(source, destination))
        if error:
            self.show_error(
                error,
                'Unable to export image to "{}"'.format(destination)
            )

    def show_spread_widget(self):
        if self.cameras_count == 1:
            spread = CaptureLeaf(capture_screen=self)
        else:
            spread = CaptureSpread(self)
        self.capture_spread_box = spread
        self.clear_spread_view_widgets()
        self.ids._spread_view.add_widget(spread)

    def clear_spread_view_widgets(self):
        '''Disables tooltips for menus and then clears widgets of spread_view.
        '''
        spread_view = self.ids._spread_view
        if spread_view.children:
            widget = spread_view.children[0]
            if isinstance(widget, (CaptureSpread, CaptureLeaf)):
                menu = widget.ids.spread_menu_bar
                menu.use_tooltips = False
            spread_view.clear_widgets()

    def on_capture_spread_box(self, screen, capture_spread):
        self._update_book_menu_bar()
        if not capture_spread:
            self.stop_autoshoot_capture()
            return
        self._update_spread_menu_bar_page_type()
        menu = self.capture_spread_box.ids.spread_menu_bar
        menu.use_tooltips = True
        menu.bind(
            on_option_select=self._on_spread_menu_bar_option_select,
            on_type_button_release=self._on_spread_type_button_release,
            on_number_button_release=self._on_spread_number_button_release
        )

    def _on_spread_menu_bar_option_select(self, spread_menu_bar, side, option):
        side = self.adjust_side(side)
        if option == 'view_source':
            self.show_original_file(None, side)
        elif option == 'delete_spread':
            self.capture_spread_box.delete_or_foldout()
        elif option == 'export':
            leaf_number = self.get_slider_bar_value(side)
            path, thumb_path = self.get_paths(leaf_number)
            self.start_image_export_filechooser(path)
        elif option == 'insert':
            leaf_number = self.get_slider_bar_value(side)
            path, thumb_path = self.get_paths(leaf_number)
            self.start_insert_filechooser(side, path)
        elif option == 'rotate':
            leaf_number = self.get_slider_bar_value(side)
            self.rotate_image(side, leaf_number)
        elif option == 'ppi':
            leaf_number = self.get_slider_bar_value(side)
            leaf_ppi = self.get_leaf_ppi(leaf_number)
            data = {'leaf_number': leaf_number, 'side': side}
            self.show_ppi_popup(leaf_number, leaf_ppi, extra_data=data)

    def show_ppi_popup(self, leaf_number, default_ppi, extra_data=None):
        popup = self.create_popup(popup_cls=EditPPIPopup,
                                  default_ppi=default_ppi,
                                  extra=extra_data)
        popup.bind(on_submit=self.on_ppi_value_submit)
        popup.open()

    def on_ppi_value_submit(self, popup, ppi_value):
        leaf_number = popup.extra['leaf_number']
        if self.scandata.get_ppi(leaf_number) != ppi_value:
            self.scandata.set_ppi(leaf_number, ppi_value)
            self.scandata.save()
            side = popup.extra['side']
            self.set_page_ppi_button(side, ppi_value)
            if self.capture_spread_box:
                stats = self.get_stats(side)
                stats['ppi'] = ppi_value
            Logger.info('CaptureScreen: Set {}ppi for leaf {}'
                        .format(ppi_value, leaf_number))

    def get_book_ppi(self):
        fallback_ppi = 300
        leaf_ppi = None
        if self.scandata is not None:
            ppi = self.scandata.get_bookdata('ppi')
            leaf_ppi = ppi
        if leaf_ppi is None:
            leaf_ppi = self.config.get('camera_ppi', None)
        if leaf_ppi is None:
            Logger.error('CaptureScreen: Unable to get camera ppi value from '
                         'scandata or scribe config. Using fallback '
                         'value of {} ppi'.format(fallback_ppi))
            leaf_ppi = fallback_ppi
        return int(leaf_ppi)

    def get_leaf_ppi(self, leaf_number):
        leaf_ppi = self.scandata.get_ppi(leaf_number)
        if leaf_ppi is None:
            return self.get_book_ppi()
        return int(leaf_ppi)

    def start_insert_filechooser(self, side, source_path):
        self.disable_capture_actions()
        _, ext = os.path.splitext(source_path)
        filters = [
            ['{} image file'.format(ext),
             '*{}'.format(ext.lower()),
             '*{}'.format(ext.upper())
            ],
        ]
        if self.config.is_true('allow_all_extensions_in_filechooser'):
            filters.append(
                ['Any file', '*']
            )
        default_path = join(os.path.expanduser('~'), '')
        callback = partial(self.on_insert_image_selection, side, source_path)
        filechooser = FileChooser()
        filechooser.bind(on_selection=callback)
        filechooser.open_file(title='Select image',
                              icon='./images/window_icon.png',
                              filters=filters,
                              path=default_path)

    def on_insert_image_selection(self, side, source_path, chooser, selection):
        if selection:
            target_path = selection[0]
            if not os.path.isfile(target_path):
                self.show_error(None,
                                '"{}" is not a file'.format(target_path))
                return
            elif not target_path.endswith(('.jpg', '.JPG', '.jpeg', '.JPEG', )) \
                 and not self.config.is_true('allow_all_extensions_in_filechooser'):
                self.show_error(None,
                                '"{}" not a JPEG file'.format(target_path))
                return
            side = self.adjust_side(side)
            leaf_number = self.get_displayed_sides()[side]
            data = self.scandata.get_page_data(leaf_number)
            angle = int(data.get('rotateDegree', 0))
            self.insert_image(source_path, target_path, angle)
            page_widget = self.get_page_widget(side)
            page_widget.reload()
        self.enable_capture_actions()

    def insert_image(self, source_path, target_path, rotate_angle=0):
        source_filename = os.path.basename(source_path)
        source_thumbnail_path = join(
            dirname(source_path), 'thumbnails', source_filename
        )
        thumbnail_size = (1500, 1000)
        if self.config.is_true('low_res_proxies'):
            thumbnail_size = (750, 500)
        image = Image.open(target_path)
        image.thumbnail(thumbnail_size)
        image = image.rotate(rotate_angle, expand=True)
        try:
            image.save(source_thumbnail_path, 'JPEG', quality=90)
            shutil.copyfile(target_path, source_path)
            Logger.info('CaptureScreen: Inserted image "{}" in place of "{}"'
                        .format(target_path, source_path))
        except Exception as error:
            message = ('Failed to insert "{}" in place of "{}"'
                       .format(target_path, source_path))
            Logger.exception('CaptureScreen: ' + message)
            self.show_error(error, message)

    def _on_spread_type_button_release(self, spread_menu_bar, side, button):
        side = self.adjust_side(side)
        self.show_page_attrs(button, side)

    def rotate_image(self, side, leaf_number):
        path, thumb_path = self.get_paths(leaf_number)
        if not os.path.exists(thumb_path):
            Logger.error('CaptureScreen: Skipping rotation because thumbnail '
                         'path does not exits: {}'.format(thumb_path))
            return
        data = self.scandata.get_page_data(leaf_number)
        path, thumb_path = self.get_paths(leaf_number)
        scandata_rotation_angle = 90

        current_degree = int(data.get('rotateDegree', 0))
        new_degree = (current_degree + scandata_rotation_angle) % 360
        self.scandata.update_rotate_degree(leaf_number, new_degree)
        self.scandata.save()

        rotate_by = convert_scandata_angle_to_thumbs_rotation(new_degree, scandata_rotation_angle)

        image = Image.open(path)
        size = (1500, 1000)  # (6000,4000)/4
        if self.config.is_true('low_res_proxies'):
            size = (750, 500)  # (6000,4000)/8
        image.thumbnail(size)
        image = image.rotate(rotate_by, expand=True)
        image.save(thumb_path, 'JPEG', quality=90)

        page_widget = self.get_page_widget(side)
        page_widget.reload()
        Logger.info('CaptureScreen: Updated leaf {} with rotation {}'
                    .format(leaf_number, new_degree))

    def show_page_attrs(self, button, side):
        self.disable_capture_actions()
        leaf_number = self.get_slider_bar_value(side)
        leaf_data = self.scandata.get_page_data(leaf_number)
        page_type = leaf_data.get('pageType', self.get_default_page_type())
        page_number = self.scandata.get_page_assertion(leaf_number)
        popup = self._page_type_form_popup
        popup.target_anchor_x = side if side != 'foldout' else 'right'
        popup.target_widget = self.get_spread_menu_bar()
        popup.default_page_type = page_type
        popup.default_page_number = page_number
        popup.extra = {'leaf_number': leaf_number, 'side': side}
        popup.open()

    def _on_page_form_popup_submit(self, popup, data):
        side = popup.extra['side']
        leaf_number = popup.extra['leaf_number']
        page_type = data['page_type']
        page_number = data['page_number']
        self.set_page_attrs(leaf_number, page_type, side, page_number)

    def get_spread_menu_bar(self):
        if self.capture_spread_box:
            return self.capture_spread_box.ids.spread_menu_bar
        else:
            capture_cover = self.ids._spread_view.children[0]
            return capture_cover.ids.leaf_menu_bar

    def _on_spread_number_button_release(self, spread_menu_bar, side, button):
        side = self.adjust_side(side)
        self.set_page_num(side)

    def show_spread(self, value):
        '''Argument `value` is page number if CaptureLeaf is used and spread
        number otherwise.
        '''
        value = int(value)
        spread_slider = self.spread_slider_bar
        if not (spread_slider.slider_min <= value <= spread_slider.slider_max):
            return
        if spread_slider.slider_value != value:
            spread_slider.slider_value = value
            return
        Logger.info('CaptureScreen: slider up at {}'.format(value))
        sides = self.get_displayed_sides()
        for side in sides:
            page_number = self.compute_page_number(side, value)
            path, thumb_path = self.get_paths(page_number)
            if os.path.exists(thumb_path):
                if os.path.exists(path) or self.downloaded_book:
                    self.set_page_widget(side, thumb_path, allow_stretch=True)
            else:
                page_widget = self.get_page_widget(side)
                # TODO: Find better way to check if camera is shooting
                if page_widget.source != scribe_globals.LOADING_IMAGE:
                    self.set_page_widget(side, scribe_globals.MISSING_IMAGE)
            stats = self.get_stats(side)
            stats['leaf_num'] = page_number
            page_data = self.scandata.get_page_data(page_number)
            page_type = self.get_default_page_type()
            stats['page_type'] = page_data.get('pageType', None) or page_type
            blur_value = page_data.get('blurriness', None)
            stats['blurriness'] = blur_value
            page_widget = self.get_page_widget(side)

            if page_data.get('is_blurry', None):
                page_widget.background_color = [1 - float(blur_value)/256, 0, .1, .6]
            else:
                page_widget.background_color = [.75, .75, .75, 1]

            ppi_value = self.get_leaf_ppi(page_number)
            stats['ppi'] = ppi_value
            stats['capture_time'] = self.scandata.get_capture_time(page_number)
            stats['notes'] = page_data.get('note', None) or ''
            self.set_page_number_button(side, page_number)
            self.set_page_ppi_button(side, ppi_value)

        if self.cameras_count != 1:
            first = spread_slider.slider_value == spread_slider.slider_min
            spread = self.capture_spread_box
            spread.ids.spread_menu_bar.use_left_menu = not first
            spread.ids._page_left.zoom_box_disabled = first

    def set_page_widget(self, side, image_path, allow_stretch=False):
        page = self.get_page_widget(side)
        page.source = image_path
        page.allow_stretch = allow_stretch

    def get_page_widget(self, side):
        if not self.capture_spread_box:
            capture_cover = self.ids._spread_view.children[0]
            if side == 'left':
                return capture_cover.ids._color_card_image
            elif side == 'right':
                return capture_cover.ids._cover_image
            raise ValueError('Unknown side: {}'.format(side))
        ids = self.capture_spread_box.ids
        if side == 'left':
            return ids._page_left
        elif side == 'right':
            return ids._page_right
        elif side == 'foldout':
            return ids.page
        raise ValueError('Unknown side: {}'.format(side))

    def get_displayed_sides(self):
        '''Returns dict {side: page_number} where side can be 'left', 'right'
        or 'foldout'. Page number is calculated from spread_slider_bar.
        '''
        value = int(self.spread_slider_bar.slider_value)
        if self.cameras_count == 1:
            return OrderedDict({'foldout': value})
        out = OrderedDict()
        out['left'] = 2 * value
        out['right'] = 2 * value + 1
        return out

    def get_capture_queue(self, side):
        if side == 'left':
            return self.scribe_widget.left_queue
        elif side == 'right':
            return self.scribe_widget.right_queue
        elif side == 'foldout':
            return self.scribe_widget.foldout_queue
        raise ValueError('Unknown side: {}'.format(side))

    def get_stats(self, side):
        if side == 'left':
            return self.capture_spread_box.left_stats
        elif side == 'right':
            return self.capture_spread_box.right_stats
        elif side == 'foldout':
            return self.capture_spread_box.stats
        raise ValueError('Unknown side: {}'.format(side))

    def get_page_number_button(self, side):
        if not self.capture_spread_box:
            if side == 'right':
                capture_cover = self.ids._spread_view.children[0]
                return capture_cover.ids.leaf_menu_bar.ids.number_button
            raise ValueError('Invalid side for capture cover: {}'.format(side))
        menu = self.capture_spread_box.ids.spread_menu_bar
        if side == 'left':
            return menu.left_number_button
        elif side == 'right':
            return menu.right_number_button
        elif side == 'foldout':
            return menu.right_number_button
        raise ValueError('Unknown side: {}'.format(side))

    def set_page_type_button(self, side, page_type):
        if self.capture_spread_box is None:
            capture_cover = self.ids._spread_view.children[0]
            # Access leaf_menu_bar of cover_leaf_menu_bar widget
            menu = capture_cover.ids.leaf_menu_bar.ids.leaf_menu_bar
            menu.page_type = page_type
        else:
            button = self.get_page_type_button(side)
            button.text = page_type

    def set_page_number_button(self, side, page_number):
        button = self.get_page_number_button(side)
        page_data = self.scandata.get_page_num(page_number)
        if not page_data:
            page_data = self.scandata.get_page_assertion(page_number)
        if page_data is None:
                button.text = ''
                button.set_color('clear')
                return
        colors = {
            'assert': 'green',
            'match': 'gray',
            'mismatch': 'red',
        }
        # TODO: Update following lines when scandata structure is same when
        # reshooting book and otherwise
        if isinstance(page_data, dict):
            # default scandata structure
            color = colors.get(page_data['type'], 'gray')
            button.text = str(page_data['num'])
            button.set_color(color)
        elif isinstance(page_data, str):
            # reshooting book
            button.text = page_data
            button.set_color('gray')
        elif isinstance(page_data, int):
            button.text = str(page_data)
            button.set_color('blue')

    def set_page_ppi_button(self, side, ppi_value):
        if self.capture_spread_box is None:
            capture_cover = self.ids._spread_view.children[0]
            menu = capture_cover.ids.leaf_menu_bar.ids.leaf_menu_bar
            menu.ppi = ppi_value
        else:
            menu = self.capture_spread_box.ids.spread_menu_bar
            if side == 'left':
                menu.left_ppi_button.text = '{}ppi'.format(ppi_value)
            elif side == 'right' or side == 'foldout':
                menu.right_ppi_button.text = '{}ppi'.format(ppi_value)

    def get_page_type_button(self, side):
        menu = self.capture_spread_box.ids.spread_menu_bar
        if side == 'left':
            return menu.left_type_button
        elif side == 'right':
            return menu.right_type_button
        elif side == 'foldout':
            return menu.right_type_button
        raise ValueError('Unknown side: {}'.format(side))

    def get_slider_bar_value(self, side):
        value = int(self.spread_slider_bar.slider_value)
        if side == 'foldout':
            return value
        elif side == 'left':
            return 2 * value
        elif side == 'right':
            return 2 * value + 1
        raise ValueError('Unknown side: {}'.format(side))

    def get_page_max_value(self):
        if isinstance(self.capture_spread_box, CaptureLeaf):
            return int(self.spread_slider_bar.slider_max)
        return 2 * int(self.spread_slider_bar.slider_max) + 1

    def get_default_page_type(self):
        if self.cameras_count == 1 and self.book_dir:
            md = get_metadata(self.book_dir)
            if md.get('source', None) != 'folio':
                return PT_FOLDOUT
        return PT_NORMAL

    def compute_page_number(self, side, value):
        if side == 'foldout':
            return value
        elif side == 'left':
            return 2 * value
        elif side == 'right':
            return 2 * value + 1
        raise ValueError('Unknown side: {}'.format(side))

    def adjust_side(self, side):
        '''Returns 'foldout' is CaptureLeaf is displayed, but returns `side`
        unchanged otherwise.
        '''
        if self.cameras_count == 1:
            return 'foldout'
        return side

    def show_image_callback(self, report, *args):
        '''This function modifies UI elements and needs to be scheduled on the
        main thread.
        '''
        Logger.info('CaptureScreen: Received camera report:{}{}'
                    .format(os.linesep, pformat(report)))
        if report[camera_system.KEY_EXTRA]['book_path'] != self.book_dir\
                    or self.manager and self.manager.current != self.name:
            Logger.warn('CaptureScreen: Not handling camera report because '
                        'user has left this screen')
            return
        camera_side = report[camera_system.KEY_SIDE]
        leaf_number = report[camera_system.KEY_EXTRA]['leaf_number']
        if not self.scandata.get_page_data(leaf_number):
            Logger.warn('CaptureScreen: Leaf data for leaf {} got deleted'
                        .format(leaf_number))
            self.camera_status[camera_side] = 1
            if self._have_cameras_returned(camera_side):
                self.spread_slider_bar.scan_button_disabled = False
            return
        camera_error = report[camera_system.KEY_ERROR]
        if camera_error is None:
            self.camera_status[camera_side] = 1
            capture_time = report[camera_system.KEY_STATS]['capture_time']
            self.scandata.set_capture_time(leaf_number, capture_time)
            self.scandata.save()
            method_name = report[camera_system.KEY_EXTRA]['capture_method']
            #if method_name == 'reshoot_spread':
            #    self._update_image_rotation(leaf_number, camera_side)
            sides = self.get_displayed_sides()
            bar = self.spread_slider_bar
            if bar.slider_value != bar.slider_max:
                Cache.remove('kv.image')
                Cache.remove('kv.texture')
            if leaf_number in sides.values():
                page_side = 'left' if leaf_number % 2 == 0 else 'right'
                self.set_page_widget(self.adjust_side(page_side),
                                     report[camera_system.KEY_THUMB_PATH],
                                     allow_stretch=True)
                if self.capture_spread_box:
                    for side, displayed_leaf_number in sides.items():
                        if displayed_leaf_number == leaf_number:
                            stats = self.get_stats(side)
                            stats['capture_time'] = capture_time
            self._safe_for_autoshoot = True
        else:
            self.camera_status[camera_side] = camera_error
            self.stop_autoshoot_capture()

        if not self._have_cameras_returned(camera_side):
            return

        if self._should_retry_capture(camera_side):
            Logger.info('CaptureScreen: Retry capture')
            report_extra = report[camera_system.KEY_EXTRA]
            extra = {'leaf_number': report_extra['leaf_number'],
                     'side': camera_side,
                     'capture_method': report_extra['capture_method']}
            popup = self.create_popup(
                popup_cls=CaptureFailurePopup,
                message=self._create_capture_error_message(camera_side),
                extra=extra
            )
            popup.bind(on_submit=self._on_capture_failure_popup_submit)
            popup.open()
        else:
            self.spread_slider_bar.scan_button_disabled = False
            if self.cameras_count == 3 \
                    and camera_side == 'foldout' \
                    and self.capture_spread_box:
                self.capture_spread_box.disable_foldout_mode()

    def _have_cameras_returned(self, camera_side):
        camera_status = self.camera_status
        if camera_side != 'foldout':
            if camera_status['left'] is None or camera_status['right'] is None:
                # Both cameras have not yet returned
                return False
        return True

    def _should_retry_capture(self, camera_side):
        camera_status = self.camera_status
        if camera_side == 'foldout':
            if camera_status['foldout'] != 1:
                return True
        else:
            if (camera_status['left'] != 1) or (camera_status['right'] != 1):
                return True
        return False

    def _update_image_rotation(self, leaf_number, camera_side):
        leaf_data = self.scandata.get_page_data(leaf_number)
        leaf_angle = int(leaf_data['rotateDegree']) % 360
        # Cast camera angle to leaf angle used by scandata
        if camera_side == 'foldout':
            camera_angle = - self.config.get_integer('default_single_camera_rotation', 180) + 180
            if self.cameras_count != 1:
                camera_angle = 0
        else:
            camera_angle = -SIDE_TO_DEGREE[camera_side] + 180
        camera_angle %= 360
        diff_angle = (camera_angle - leaf_angle)
        if diff_angle != 0:
            # Rotate image by inverse difference angle because scandata
            # angle is an inverse of pillow angle
            angle = -diff_angle % 360
            path, thumb_path = self.get_paths(leaf_number)
            image = Image.open(thumb_path)
            image = image.rotate(angle, expand=True)
            image.save(thumb_path, 'JPEG', quality=90)
            if leaf_number in self.get_displayed_sides().values():
                page_widget = self.get_page_widget(camera_side)
                page_widget.reload()
            Logger.info('CaptureScreen: Image of leaf {} rotated by {}'
                        .format(leaf_number, angle))

    def _create_capture_error_message(self, side):
        message = 'There was an error during image capture.'
        camera_status = self.camera_status
        if side == 'foldout':
            message += '\n\nError capturing the FOLDOUT page: {e}' \
                       .format(e=camera_status['foldout'])
        else:
            if camera_status['left'] != 1:
                message += '\n\nError capturing the LEFT page: {e}' \
                           .format(e=camera_status['left'])
            if camera_status['right'] != 1:
                message += '\n\nError capturing the RIGHT page: {e}' \
                           .format(e=camera_status['right'])
        return message

    def _on_capture_failure_popup_submit(self, popup, option):
        if option == popup.OPTION_RETRY_CAPTURE:
            popup.dismiss(animation=False)
            method_name = popup.extra['capture_method']
            reshoot_method = self._reshoot_methods[method_name]
            if method_name == 'capture_foldout':
                if self.cameras_count == 3:
                    leaf_number = popup.extra['leaf_number']
                    side = 'left' if leaf_number % 2 == 0 else 'right'
                else:
                    side = popup.extra['side']
                reshoot_method(side)
            elif method_name == 'capture_spread' \
                    or method_name == 'reshoot_spread':
                # Enabling scan_button here, so that capture_spread can work
                self.spread_slider_bar.scan_button_disabled = False
                reshoot_method()
            else:
                reshoot_method()
        elif option == popup.OPTION_GOTO_CALIBRATION:
            popup.dismiss(animation=False)
            self.goto_calibration(extra=self.create_state())

    def get_paths(self, page_num):
        img = '{n:04d}.jpg'.format(n=page_num)
        path = join(self.book_dir, img)
        thumb_path = join(self.book_dir, 'thumbnails', img)
        return path, thumb_path

    def show_error(self, e, msg):
        popup = self.create_popup(
            title='Error', content=Label(text=msg),
            size_hint=(None, None), size=('400dp', '300dp')
        )
        popup.open()

    def show_original_file(self, button, side):
        side = self.adjust_side(side)
        leaf_number = self.get_slider_bar_value(side)
        jpg = '{n:04d}.jpg'.format(n=leaf_number)
        file_url = os.path.join(self.book_dir, jpg)
        firefox = webbrowser.get('firefox')
        firefox.open(file_url)

    def set_leaf_note(self, leaf_number, note):
        scandata = self.scandata
        note = note.strip()
        if scandata.get_note(leaf_number) != note:
            scandata.set_note(leaf_number, note)
            scandata.save()
            if note:
                Logger.info(
                    'CaptureScreen: Updated leaf %d with note: %s'
                    % (leaf_number, '\n%s' % note if '\n' in note else note)
                )
            else:
                Logger.info('CaptureScreen: Removed note from leaf {}'
                            .format(leaf_number))

    def set_page_attrs(self, leaf_num, page_type, side, page_assertion):
        scandata = self.scandata
        scandata.update_page(leaf_num, page_type, page_assertion)
        scandata.compute_page_nums(scandata.get_max_leaf_number())
        scandata.save()
        if self.capture_spread_box is None:
            capture_cover = self.ids._spread_view.children[0]
            # Access leaf_menu_bar of cover_leaf_menu_bar widget
            menu = capture_cover.ids.leaf_menu_bar.ids.leaf_menu_bar
            menu.page_type = page_type
            self.set_page_number_button('right', leaf_num)
            return
        menu = self.capture_spread_box.ids.spread_menu_bar
        if side == 'left':
            stats = self.capture_spread_box.left_stats
            stats['page_type'] = page_type
            self.show_page_num(menu.left_number_button, leaf_num)
            self.show_page_num(menu.right_number_button, leaf_num + 1)
            menu.left_type_button.text = page_type
        elif side == 'right':
            stats = self.capture_spread_box.right_stats
            stats['page_type'] = page_type
            self.show_page_num(menu.left_number_button, leaf_num - 1)
            self.show_page_num(menu.right_number_button, leaf_num)
            menu.right_type_button.text = page_type
        elif side == 'foldout':
            stats = self.capture_spread_box.stats
            stats['page_type'] = page_type
            self.set_page_number_button(side, leaf_num)
            menu.right_type_button.text = page_type

    def set_page_num(self, side):
        '''The page number bubble was clicked. Toggle the assertion on/off if
        the page was previously asserted, remove the page num assertion. If it
        was not asserted, then create the assertion.
        '''
        sides = self.get_displayed_sides()
        leaf_number = sides[side]
        scandata = self.scandata
        page_assert_data = scandata.get_page_num(leaf_number)
        if page_assert_data is None:
            return
        if isinstance(page_assert_data, dict):
            if page_assert_data['type'] == 'assert':
                # Toggle assertion off
                num = None
            else:
                # Toggle on to whatever the autofill value is
                num = page_assert_data['num']
        elif isinstance(page_assert_data, str):
            # TODO: Remove in 1.50+ version of the app
            # because page_assert_data is string in downloaded scanadata.json
            num = int(page_assert_data)
            if not self.downloaded_book:
                num = page_assert_data
            scandata.add_page_num(leaf_number, num, 'assert')
        scandata.update_page_assertion(leaf_number, num)
        scandata.compute_page_nums(scandata.get_max_leaf_number())
        scandata.save()
        for side, leaf_number in sides.items():
            self.set_page_number_button(side, leaf_number)

    def show_page_num(self, widget, leaf_num):
        page_num = self.scandata.get_page_num(leaf_num)
        if page_num is None:
            widget.text = ''
            widget.set_color('clear')
            return
        colors = {
            'assert': 'green',
            'match': 'gray',
            'mismatch': 'red',
        }
        color = colors.get(page_num['type'], 'gray')
        widget.text = str(page_num['num'])
        widget.set_color(color)

    def disable_upload_and_send_buttons(self):
        ids = self.book_menu_bar.ids
        ids.send_to_station.disabled = True
        ids.upload_and_new_book_button.disabled = True
        ids.upload_button.disabled = True

    def goto_calibration(self, popup=None, extra=None):
        if popup is not None:
            popup.dismiss()
        self.scribe_widget.show_calibration_screen(
            target_screen='capture_screen',
            extra=extra
        )

    def create_popup(self, **kwargs):
        popup_cls = kwargs.pop('popup_cls', Popup)
        popup = popup_cls(**kwargs)
        popup.bind(on_open=self._on_popup_open,
                   on_dismiss=self._on_popup_dismiss)
        return popup

    def create_camera_kwargs(self, camera_side, leaf_number,
                             capture_method=None):
        path, thumb_path = self.get_paths(leaf_number)
        extra = {'leaf_number': leaf_number,
                 'capture_method': capture_method,
                 'book_path': self.book_dir}
        return {
            camera_system.KEY_CALLBACK: self.show_image_callback,
            camera_system.KEY_SIDE: camera_side,
            camera_system.KEY_PATH: path,
            camera_system.KEY_THUMB_PATH: thumb_path,
            camera_system.KEY_EXTRA: extra
        }

    def create_state(self):
        return {
            'book_dir': self.book_dir,
            'slider_value': self.spread_slider_bar.slider_value
        }

    def _on_popup_open(self, popup):
        Logger.info(u'CaptureScreen: Opened "{}" popup'
                    .format(self._get_popup_title(popup)))
        self.stop_autoshoot_capture()
        self.disable_capture_actions()
        self.use_tooltips = False

    def _on_popup_dismiss(self, popup):
        Logger.info(u'CaptureScreen: Dismissed "{}" popup'
                    .format(self._get_popup_title(popup)))
        self.enable_capture_actions()
        self.use_tooltips = True

    def _get_popup_title(self, popup):
        return getattr(popup, 'title', None) or type(popup).__name__

    def on_book_reset(self):
        pass

    def on_start_new_book(self):
        pass

    def on_edit_metadata(self):
        pass
