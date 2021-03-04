import webbrowser
from os.path import join, dirname, exists

from kivy.cache import Cache
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen

from ia_scribe.cameras import camera_system
from ia_scribe.exceptions import DiskFullError
from ia_scribe.scribe_globals import LOADING_IMAGE, MISSING_IMAGE, FAKE_IMAGE
from ia_scribe.uix.behaviors.tooltip import TooltipScreen
from ia_scribe.uix.components.buttons.buttons import ColorButton
from ia_scribe.uix.components.poppers.popups import (
    PageTypeFormPopup,
    CaptureFailurePopup,
    QuestionPopup
)
from ia_scribe.uix_backends.reshoot_screen_backend import ReShootScreenBackend
from ia_scribe.utils import get_string_value_if_list

Builder.load_file(join(dirname(__file__), 'reshoot_screen.kv'))


class ReShootTitleBar(BoxLayout):

    identifier = StringProperty()
    title = StringProperty()


class ReShootLeafInfoPanel(GridLayout):

    hand_side = StringProperty(None, allownone=True)
    leaf_number = ObjectProperty(None, allownone=True, baseclass=int)
    page_number = ObjectProperty(None, allownone=True, baseclass=int)
    page_type = StringProperty(None, allownone=True)
    notes = StringProperty(None, allownone=True)

    EVENT_EDIT_START = 'on_edit_start'
    EVENT_EDIT_END = 'on_edit_end'
    EVENT_NOTE_SUBMIT = 'on_note_submit'

    __events__ = (EVENT_EDIT_START, EVENT_EDIT_END, EVENT_NOTE_SUBMIT)

    def on_kv_post(self, base_widget):
        super(ReShootLeafInfoPanel, self).on_kv_post(base_widget)
        self.ids.note_input.bind(
            note_input_displayed=self._on_note_input_displayed
        )

    def format_string(self, value):
        return 'NULL' if value is None else value

    def format_int(self, value):
        return 'NULL' if value is None else str(value)

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


class SpreadBox(BoxLayout):

    original_image = ObjectProperty(None, allownone=True)
    reshoot_image = ObjectProperty(None, allownone=True)


class ReShootScreen(TooltipScreen, Screen):

    def __init__(self, **kwargs):
        self._camera_status = {'left': None, 'right': None, 'foldout': None}
        self._page_type_form_popup = popup = self.create_popup(
            popup_cls=PageTypeFormPopup,
            target_anchor_x='right',
            page_number_input_disabled=True
        )
        popup.fbind('on_submit', self._on_page_type_form_popup_submit)
        self.backend = ReShootScreenBackend()
        self.book = None
        self.reopen_at = None
        self.scandata = None
        self.scribe_widget = None
        self.screen_manager = None
        super(ReShootScreen, self).__init__(**kwargs)
        Clock.schedule_once(self._postponed_init)

    def _postponed_init(self, *args):
        self._bind_menu_bar()
        self._bind_leaf_info_panel()
        self._bind_slider_menu_bar()
        self._bind_backend()

    def _bind_menu_bar(self):
        menu = self.ids.menu_bar
        menu.fbind(menu.EVENT_OPTION_SELECT, self._on_menu_option_select)

    def _bind_leaf_info_panel(self):
        panel = self.ids.leaf_info_panel
        panel.fbind(panel.EVENT_NOTE_SUBMIT, self._on_leaf_note_submit)
        panel.fbind(panel.EVENT_EDIT_START, self._on_popup_open)
        panel.fbind(panel.EVENT_EDIT_END, self._on_popup_dismiss)

    def _bind_slider_menu_bar(self):
        menu = self.ids.slider_menu_bar
        fbind = menu.fbind
        fbind(menu.EVENT_OPTION_SELECT, self._on_slider_menu_bar_option_select)
        fbind(menu.EVENT_SLIDER_VALUE_UP, self._on_slider_menu_value_up)
        fbind('slider_min', self.update_slider_menu_tooltip)
        fbind('slider_max', self.update_slider_menu_tooltip)
        fbind('slider_value', self.update_slider_menu_tooltip)

    def _bind_backend(self):
        backend = self.backend
        backend.fbind(backend.EVENT_CAPTURE_LEAF, self._on_capture_leaf)
        backend.fbind(backend.EVENT_ROTATE_LEAF, self._on_leaf_rotate)
        backend.fbind(backend.EVENT_CURRENT_LEAF, self._on_current_leaf)
        backend.fbind(backend.EVENT_PAGE_TYPE, self._on_page_type)
        backend.fbind(backend.EVENT_SHOW_ORIGINAL_FILE,
                      self._on_show_original_file)
        backend.fbind(backend.EVENT_SHOW_RESHOOT_FILE,
                      self._on_show_reshoot_file)
        backend.fbind(backend.EVENT_SHOW_PAGE_TYPE_FORM_POPUP,
                      self.open_page_type_form_popup)
        backend.fbind(backend.EVENT_GO_BACK, self.goto_rescribe_screen)

    def setup_title_bar(self):
        md = self.backend.get_book_metadata()
        bar = self.ids.title_bar
        bar.identifier = md['identifier']
        title = get_string_value_if_list(md, 'title') or u'-'
        creator = get_string_value_if_list(md, 'creator') or u'-'
        language = get_string_value_if_list(md, 'language') or u'-'
        menu_title = u'{}, {} ({})'.format(title, creator, language)
        bar.title = menu_title

    def setup_menu_bar(self):
        backend = self.backend
        menu_bar = self.ids.menu_bar
        menu_bar.reshoot_menu_disabled = not backend.is_reshoot_leaf_ready()
        leaf_number = backend.get_current_leaf_number()
        leaf_data = self.scandata.get_page_data(leaf_number)
        menu_bar.page_type = leaf_data['pageType']
        self._page_type_form_popup.target_widget = menu_bar

    def setup_slider_menu_bar(self):
        backend = self.backend
        max_index = max(0, backend.get_leafs_count() - 1)
        menu = self.ids.slider_menu_bar
        menu.slider_min = 0
        menu.slider_max = max_index
        menu.slider_value = backend.get_current_leaf_index()
        menu.scan_button_disabled = not backend.can_capture_spread()
        menu.switch_button_disabled = not backend.can_switch_cameras()
        self.update_slider_menu_tooltip(menu)

    def update_slider_menu_tooltip(self, *args):
        leaf_number = self.backend.get_current_leaf_number()
        data = self.backend.get_leaf_data()
        page_number = data['page_number']
        if page_number is None:
            page_number = '-'
        menu = self.ids.slider_menu_bar
        menu.slider_tooltip = 'Leaf {} | Page {}'.format(leaf_number, page_number)

    def setup_leaf_info_panel(self):
        data = self.backend.get_leaf_data()
        panel = self.ids.leaf_info_panel
        panel.hand_side = data.get('hand_side', None)
        panel.leaf_number = self.backend.get_current_leaf_number()
        panel.page_number = data.get('page_number', None)
        panel.page_type = data.get('page_type', None)
        panel.notes = data.get('note', None)

    def setup_leaf_boxes(self):
        self.show_original_leaf()
        self.show_reshoot_leaf()

    def show_original_leaf(self):
        path, thumb_path = self.backend.get_current_original_paths()
        image_path = thumb_path if exists(thumb_path) else MISSING_IMAGE
        image = self.ids.spread_box.original_image
        image.allow_stretch = True
        image.source = image_path

    def show_reshoot_leaf(self):
        path, thumb_path = self.backend.get_current_reshoot_paths()
        image_path = thumb_path if exists(thumb_path) else FAKE_IMAGE
        image = self.ids.spread_box.reshoot_image
        image.allow_stretch = True
        image.source = image_path
        image.reload()

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

    def open_page_type_form_popup(self, *args):
        leaf_number = self.backend.get_current_leaf_number()
        leaf_data = self.scandata.get_page_data(leaf_number)
        popup = self._page_type_form_popup
        popup.default_page_type = leaf_data['pageType']
        popup.extra = {'leaf_number': leaf_number}
        popup.open()

    def show_error(self, e, msg):
        # Called in main thread
        popup = Popup(title='Error', content=Label(text=msg),
                      auto_dismiss=False,
                      size_hint=(None, None), size=(400, 300))
        popup.open()

    def goto_calibration(self, *args):
        self.screen_manager.transition.direction = 'right'
        self.screen_manager.current = 'calibration_screen'

    def goto_rescribe_screen(self, *args):
        self.screen_manager.transition.direction = 'right'
        self.screen_manager.current = 'rescribe_screen'

    def create_popup(self, **kwargs):
        popup_cls = kwargs.pop('popup_cls', Popup)
        popup = popup_cls(**kwargs)
        popup.bind(on_open=self._on_popup_open,
                   on_dismiss=self._on_popup_dismiss)
        return popup

    def on_pre_enter(self, *args):
        # If we re-entered a book after a camera calibration issue, we may have
        # stale images in the cache
        # print "CONFIGURATION OK?" + str(configuration_ok)
        # If metadata is not set correctly, abort
        # if not configuration_ok:
        #     self.abort_shooting()
        #     return
        Cache.remove('kv.image')
        Cache.remove('kv.texture')
        backend = self.backend
        backend.book = self.book
        backend.reopen_at = self.reopen_at
        backend.scandata = self.scandata
        backend.camera_system = self.scribe_widget
        backend.window = self.get_root_window()
        backend.logger = Logger
        backend.init()
        Clock.schedule_once(self._on_backend_init)

    def on_enter(self, *args):
        super(ReShootScreen, self).on_enter(*args)
        self.backend.enable_keyboard_actions()

    def on_pre_leave(self, *args):
        super(ReShootScreen, self).on_pre_leave(*args)
        self.backend.disable_keyboard_actions()
        self.backend.reset()

    def on_disabled(self, instance, disabled):
        self.backend.disable_keyboard_actions() \
            if disabled else self.backend.enable_keyboard_actions()

    def _on_backend_init(self, *args):
        self.setup_title_bar()
        self._on_current_leaf(self.backend)

    def _on_current_leaf(self, backend, *args):
        self.setup_menu_bar()
        self.setup_slider_menu_bar()
        self.setup_leaf_info_panel()
        self.setup_leaf_boxes()
        Logger.info('ReShootScreen: Displayed leaf {}'
                    .format(self.backend.get_current_leaf_number()))

    def _on_leaf_rotate(self, backend, *args):
        self.ids.spread_box.reshoot_image.reload()

    def _on_capture_leaf(self, backend, report):
        error = report.get(camera_system.KEY_ERROR, None)
        if isinstance(error, DiskFullError):
            content = ColorButton(text='OK')
            popup = self.create_popup(
                title='Error: the disk is full',
                content=content, auto_dismiss=False,
                size_hint=(None, None), size=('230dp', '100dp')
            )
            content.bind(on_release=popup.dismiss)
            popup.open()
        if report.get(camera_system.KEY_CAPTURE_START, False):
            self._on_capture_leaf_start()
        elif report.get(camera_system.KEY_CAPTURE_END, False):
            self._on_capture_leaf_end(report)

    def _on_capture_leaf_start(self):
        for side in self._camera_status:
            self._camera_status[side] = None
        self.ids.slider_menu_bar.scan_button_disabled = True
        self.ids.menu_bar.reshoot_menu_disabled = True
        image = self.ids.spread_box.reshoot_image
        image.allow_stretch = False
        image.source = LOADING_IMAGE

    def _on_capture_leaf_end(self, report):
        side = report[camera_system.KEY_SIDE]
        thumb_path = report[camera_system.KEY_THUMB_PATH]
        error = report.get(camera_system.KEY_ERROR, None)
        if not self.backend.is_initialized():
            # Test if backend is_initialized so that app doesn't crash in case
            # when capture retry is running and user leaves this screen
            Logger.info('ReShootScreen: Capture finished, but user left the '
                        'screen')
            return
        if error is None:
            self._camera_status[side] = 1
            self.show_reshoot_leaf()
        else:
            self._camera_status[side] = error
        if side != 'foldout' and self._camera_status[side] is None:
            Logger.info('ReShootScreen: {} camera has not yet returned'
                        .format(side.capitalize()))
            return

        if self._camera_status[side] != 1:
            # Retry capture
            self.backend.delete_current_spread()
            popup = self.create_popup(
                popup_cls=CaptureFailurePopup,
                message=self._create_capture_error_message(side),
            )
            popup.bind(on_submit=self._on_capture_failure_popup_submit)
            popup.open()
        else:
            self.ids.slider_menu_bar.scan_button_disabled = False
            self.ids.menu_bar.reshoot_menu_disabled = False

    def _create_capture_error_message(self, side):
        message = 'There was an error during image capture.'
        if side == 'foldout':
            message += '\n\nError capturing the FOLDOUT page: {e}' \
                       .format(e=self._camera_status['foldout'])
        else:
            if self._camera_status['left'] != 1:
                message += '\n\nError capturing the LEFT page: {e}' \
                           .format(e=self._camera_status['left'])
            if self._camera_status['right'] != 1:
                message += '\n\nError capturing the RIGHT page: {e}' \
                           .format(e=self._camera_status['right'])
        return message

    def _on_capture_failure_popup_submit(self, popup, option):
        if option == popup.OPTION_RETRY_CAPTURE:
            popup.dismiss(animation=False)
            Logger.info('ReShootScreen: Retry capture')
            self.backend.capture_spread()
        elif option == popup.OPTION_GOTO_CALIBRATION:
            popup.dismiss(animation=False)
            self.goto_calibration()

    def _on_page_type(self, backend, page_type):
        self.ids.leaf_info_panel.page_type = page_type
        self.ids.menu_bar.page_type = page_type

    def _on_menu_option_select(self, menu, option):
        if option == 'view_original':
            self.backend.show_original_file()
        elif option == 'view_reshoot':
            self.backend.show_reshoot_file()
        elif option == 'page_type':
            self.backend.show_page_type_form_popup()
        elif option == 'rotate':
            self.backend.rotate_reshoot_leaf()

    def _on_slider_menu_bar_option_select(self, menu, option):
        if option == 'capture_spread':
            self.backend.capture_spread()
        elif option == 'go_back':
            self.backend.goto_rescribe_screen()
        elif option == 'switch_cameras':
            self.backend.switch_cameras()

    def _on_slider_menu_value_up(self, menu, value):
        self.backend.set_current_leaf_index(int(value))

    def _on_page_type_form_popup_submit(self, popup, data):
        Logger.info('ReShootScreen: {} returned data: {}'
                    .format(type(popup).__name__, data))
        page_type = data['page_type']
        leaf_number = popup.extra['leaf_number']
        self.backend.update_page_type(leaf_number, page_type)

    def _on_show_original_file(self, *args):
        path, thumb_path = self.backend.get_current_original_paths()
        firefox = webbrowser.get('firefox')
        firefox.open(thumb_path)

    def _on_show_reshoot_file(self, *args):
        path, thumb_path = self.backend.get_current_reshoot_paths()
        firefox = webbrowser.get('firefox')
        firefox.open(path)

    def _on_leaf_note_submit(self, panel, note):
        self.backend.save_leaf_note(note)
        self.setup_leaf_info_panel()

    def _on_popup_open(self, *args):
        self.backend.disable_keyboard_actions()
        self.use_tooltips = False

    def _on_popup_dismiss(self, *args):
        self.use_tooltips = True
        self.backend.enable_keyboard_actions()
