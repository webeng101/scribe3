from os.path import join, dirname, exists, expanduser, basename

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen

from ia_scribe.book.metadata import get_metadata, set_metadata
from ia_scribe.book.scandata import ScanData
from ia_scribe.scribe_globals import MISSING_IMAGE
from ia_scribe.uix.actions.book_upload import UploadCorrectionsBookActionMixin
from ia_scribe.uix.behaviors.tooltip import TooltipScreen, TooltipControl
from ia_scribe.uix.screens.corrections.book_info_panel import NONE_STR
from ia_scribe.uix.components.poppers.popups import InfoPopup, BookNotesPopup
from ia_scribe.uix.screens.corrections.reshoot_screen import ReShootScreen
from ia_scribe.book.library import Library

Builder.load_file(join(dirname(__file__), 'rescribe_screen.kv'))


class ReScribeScreenMenuBar(TooltipControl, BoxLayout):

    EVENT_OPTION_SELECT = 'on_option_select'
    OPTION_PUBLIC_NOTES = 'public_notes'
    OPTION_INTERNAL_NOTES = 'internal_notes'
    OPTION_UPLOAD = 'upload'
    OPTION_FIRST_LEAF = 'show_first_leaf'

    identifier = StringProperty()
    upload_button_disabled = BooleanProperty(False)
    reshooting_button_disabled = BooleanProperty(False)

    __events__ = (EVENT_OPTION_SELECT,)

    def on_option_select(self, option):
        pass


class ReScribeScreen(TooltipScreen, Screen):

    cover_image = StringProperty(MISSING_IMAGE)
    book = ObjectProperty(None)
    scandata = ObjectProperty(None)
    scribe_widget = ObjectProperty(None)
    screen_manager = ObjectProperty(None)

    def __init__(self, **kwargs):
        self._note_leafs = []
        self.book_obj = None
        super(ReScribeScreen, self).__init__(**kwargs)
        Clock.schedule_once(self._postponed_init)

    def _postponed_init(self, *args):
        menu = self.ids.menu_bar
        menu.fbind(menu.EVENT_OPTION_SELECT, self.on_menu_bar_option_select)
        view = self.ids.note_leafs_view
        view.fbind(view.EVENT_LEAF_SELECT, self.on_note_leaf_select)
        self._books_db = Library()

    def on_pre_enter(self):
        self.load_scandata()
        self.load_note_leafs()
        self.setup_menu_bar()
        self.setup_book_info_panel()
        self.setup_note_leafs_view()

    def load_scandata(self):
        book_path = self.book['path']
        book_uuid = basename(book_path)
        self.book_obj = self._books_db.get_book(book_uuid)
        self.scandata = ScanData(book_path, downloaded=True)
        Logger.info('ReScribeScreen: Loaded scandata from directory: {}'
                    .format(book_path))

    def load_note_leafs(self):
        leafs = self._note_leafs
        del leafs[:]
        scandata = self.scandata
        book_path = self.book['path']
        original_path = join(book_path, 'thumbnails')
        reshoot_path = join(book_path, 'reshooting', 'thumbnails')
        for note_leaf in scandata.iter_flagged_leafs():
            leaf_data = scandata.get_page_data(note_leaf)
            image_name = '{:04d}.jpg'.format(note_leaf)
            reshoot_image_path = join(reshoot_path, image_name)
            page_number = leaf_data.get('pageNumber', None)
            new_leaf_data = {
                'original_image': join(original_path, image_name),
                'reshoot_image': reshoot_image_path,
                'leaf_number': note_leaf,
                'page_number': self._get_page_number(page_number),
                'page_type': leaf_data['pageType'],
                'note': leaf_data.get('note', None) or u'',
                'status': 1 if exists(reshoot_image_path) else 0
            }
            leafs.append(new_leaf_data)

    def _get_page_number(self, page_number_data):
        # TODO: Remove this method when scandata structure becomes the same
        # for reshooting mode and otherwise
        if page_number_data:
            if isinstance(page_number_data, dict):
                page_number = page_number_data.get('num', None)
                return None if page_number is None else int(page_number)
            elif isinstance(page_number_data, str):
                return int(page_number_data)
        return None

    def setup_menu_bar(self):
        menu = self.ids.menu_bar
        menu.identifier = self.book['identifier']
        #menu.upload_button_disabled = not self.is_rescribing_complete()
        menu.reshooting_button_disabled = not bool(self._note_leafs)

    def setup_book_info_panel(self):
        panel = self.ids.book_info_panel
        panel.scroll_y = 1.0
        cover_image = join(self.book['path'], 'thumbnails', '0001.jpg')
        if not exists(cover_image):
            cover_image = MISSING_IMAGE
        panel.cover_image = cover_image
        panel.claimer = self.get_claimer()
        panel.update_from_metadata(get_metadata(self.book['path']))

    def get_claimer(self):
        path = join(expanduser(self.book['path']), 'claimer')
        if exists(path):
            with open(path, 'r') as f:
                return f.read() or NONE_STR
        return NONE_STR

    def setup_note_leafs_view(self):
        view = self.ids.note_leafs_view
        view.leafs[:] = self._note_leafs
        view.refresh_views()

    def popup_dismiss_to_home(self, popup, *args):
        popup.dismiss(animation=False)
        self.go_to_home()

    def go_to_home(self, *args, **kwargs):
        self.screen_manager.transition.direction = 'left'
        self.screen_manager.current = 'upload_screen'

    def on_menu_bar_option_select(self, menu, option):
        if option == menu.OPTION_UPLOAD:
            self.package_and_schedule_for_upload()
        elif option == menu.OPTION_FIRST_LEAF:
            leaf_number = self.find_first_non_reshoot_leaf_number()
            if leaf_number:
                self.open_book_at_leaf(leaf_number)
        elif option == menu.OPTION_PUBLIC_NOTES:
            metadata = get_metadata(self.book['path'])
            notes = metadata.get('notes', None) or ''
            popup = BookNotesPopup(title='Edit public book notes', notes=notes)
            popup.bind(on_submit=self.on_book_notes_submit)
            popup.open()
        elif option == menu.OPTION_INTERNAL_NOTES:
            internal_notes = self.scandata.get_internal_book_notes() or ''
            popup = BookNotesPopup(title='Edit internal book notes',
                                   notes=internal_notes)
            popup.bind(on_submit=self.on_internal_book_notes_submit)
            popup.open()

    def on_book_notes_submit(self, popup, notes):
        metadata = get_metadata(self.book['path'])
        metadata_notes = metadata.get('notes', None) or ''
        notes = notes.strip()
        if metadata_notes != notes:
            if notes:
                metadata['notes'] = notes
                message = 'Saved public book notes: %s' \
                          % ('\n%s' % notes if '\n' in notes else notes)
            else:
                metadata.pop('notes', None)
                message = 'Removed public book notes'
            set_metadata(metadata, self.book['path'])
            Logger.info('ReScribeScreen: %s' % message)
            self.book_obj.reload_metadata()

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
            Logger.info('ReScribeScreen: %s' % message)
            self.book_obj.reload_scandata()

    def on_note_leaf_select(self, note_leafs_view, note_leaf):
        self.open_book_at_leaf(note_leaf['leaf_number'])

    def find_first_non_reshoot_leaf_number(self):
        for note_leaf_data in self._note_leafs:
            if note_leaf_data['status'] == 0:
                return note_leaf_data['leaf_number']
        try:
            ret = self._note_leafs[0]['leaf_number']
            return ret
        except:
            return None

    def open_book_at_leaf(self, leaf_number):
        Logger.debug('ReScribeScreen: Trying to open book with id: {}'
                     .format(self.book['identifier']))
        screen_name = 'reshoot_screen'
        try:
            capture_screen = self.screen_manager.get_screen(screen_name)
        except Exception:
            capture_screen = ReShootScreen(name=screen_name)
            self.screen_manager.add_widget(capture_screen)
            capture_screen.pos = self.screen_manager.pos
        capture_screen.book = self.book
        capture_screen.reopen_at = leaf_number
        capture_screen.scandata = self.scandata
        capture_screen.screen_manager = self.screen_manager
        capture_screen.scribe_widget = self.scribe_widget
        '''
        target_screen = screen_name
        models, ports = self.scribe_widget.cameras.get_cameras()
        camera_ports = self.scribe_widget.cameras.camera_ports
        if camera_ports['left'] not in ports:
            target_screen = 'calibration_screen'
        if camera_ports['right'] not in ports:
            target_screen = 'calibration_screen'
        foldout_port = camera_ports['foldout']
        if foldout_port is not None and foldout_port not in ports:
            target_screen = 'calibration_screen'
        if target_screen == 'calibration_screen':
            screen = self.screen_manager.get_screen('calibration_screen')
            screen.target_screen = 'reshoot_screen'
            self.screen_manager.transition.direction = 'left'
            self.screen_manager.current = target_screen
        else:
        '''
        self.screen_manager.transition.direction = 'left'
        self.screen_manager.current = screen_name

    def is_rescribing_complete(self):
        if not self._note_leafs:
            return False
        for leaf_data in self._note_leafs:
            if not exists(leaf_data['reshoot_image']):
                return False
        return True

    def package_and_schedule_for_upload(self):
        if self.is_rescribing_complete():
            self.action = UploadCorrectionsBookActionMixin(
                book=self.book_obj,
                task_scheduler=self.scribe_widget.task_scheduler,
                done_action_callback=self.go_to_home
            )
            self.action.display()
        else:
            msg = 'ReScribeScreen: Book is not done rescribing'
            popup = InfoPopup(
                title='Error',
                message=msg,
                auto_dismiss=False
            )
            popup.bind(on_submit=popup.dismiss)
            popup.open()
            Logger.error(msg)
