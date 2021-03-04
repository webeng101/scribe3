import subprocess
import time
import webbrowser
from genericpath import exists
from os.path import join, dirname

from kivy import Logger
from kivy.clock import Clock
from kivy.compat import text_type
from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout

from ia_scribe.book.library import Library
from ia_scribe.book.metadata import get_metadata
from ia_scribe.uix.behaviors.form import FormBehavior
from ia_scribe.uix.behaviors.tooltip import TooltipBehavior, TooltipControl
from ia_scribe.uix.constants import BOOK_STATUS_OPTIONS_TABLE
from ia_scribe.uix.components.overlay.overlay_view import OverlayView
from ia_scribe.uix.components.info_box.info_box import InfoBox
from ia_scribe.book.upload_status import status_human_readable, UploadStatus, ERROR_STATES
from ia_scribe.scribe_globals import LOADING_IMAGE

Builder.load_file(join(dirname(__file__), 'book_menu_popup.kv'))
NONE_STR = '--'


class BookMenuPopupInfoBox(TooltipBehavior, InfoBox):
    pass

class BookMenuPopupLogPanel(BoxLayout):

    log = StringProperty()
    state = StringProperty('close')


class BookMenuPopup(TooltipControl, FormBehavior, OverlayView):

    image = StringProperty()
    media_type = StringProperty(allownone=False)
    book_path = StringProperty(NONE_STR)
    title = StringProperty(NONE_STR)
    creator = StringProperty(NONE_STR)
    volume = StringProperty(NONE_STR)
    boxid = StringProperty(NONE_STR)
    uuid = StringProperty(NONE_STR)
    identifier = StringProperty(NONE_STR)
    isbn = StringProperty(NONE_STR)
    shiptracking = StringProperty(NONE_STR)
    status = StringProperty(NONE_STR)
    status_numeric = StringProperty(NONE_STR)
    next_states = StringProperty(NONE_STR)
    path_to_success = StringProperty(NONE_STR)
    operator = StringProperty(NONE_STR)
    edit_date = StringProperty(NONE_STR)
    update_date = StringProperty(NONE_STR)
    create_date = StringProperty(NONE_STR)
    leafs = StringProperty(NONE_STR)
    ppi = StringProperty(NONE_STR)
    error_msg = StringProperty(NONE_STR)
    task_msg = StringProperty(NONE_STR)
    worker_log = StringProperty()
    loading_image = LOADING_IMAGE

    _has_identifier = BooleanProperty(False)

    def __init__(self, **kwargs):
        self.book = None
        self._book_obj = None
        self._books_db = Library()
        self._show_advanced_options = False
        self._log_panel = None
        self._log_displayed = False
        self._trigger_update = Clock.create_trigger(self._update, -1)
        super(BookMenuPopup, self).__init__(**kwargs)
        self.use_tooltips = True
        Clock.schedule_once(self._postponed_init, -1)

    def _postponed_init(self, *args):
        menu = self.ids.entry_box
        menu.fbind('on_selection', self._on_option_selection)

    def init_from_data(self, book):
        self.book = book
        self._book_obj = self._books_db.get_item(book['uuid'])
        self._book_obj.subscribe(self._trigger_update)
        self._update()

    def _update(self, *args, **kwargs):
        self._update_attributes()
        self._update_from_metadata()
        self._update_ppi_from_scandata()
        self._update_book_options()
        if self._book_obj.is_locked():
            self.lock_controls()
            owner = self._book_obj.worker_lock
            self.task_msg = 'This book is being worked on by {}'.format(owner)
        else:
            self.task_msg = ''
            self.unlock_controls()

    def _update_attributes(self):
        book_obj = self._book_obj
        self.uuid = self.book['uuid']
        self.media_type = self.book.get('type').lower()
        self.book_path = book_obj.path
        self.error_msg = self.book.get('error', None) \
                         or book_obj.msg if book_obj.msg else None \
                         or book_obj.error if book_obj.error else None \
                         or ''
        status_tag = book_obj.status
        self.status = status_human_readable.get(status_tag, status_tag)
        self.status_numeric = '%s' % book_obj.get_numeric_status()

        if int(self.status_numeric) in ERROR_STATES:
            self.ids.status_numeric_button.rgba= (0.5, 0, 0, 1)
        else:
            self.ids.status_numeric_button.rgba = (0, 0.28, 0.42, .7)

        self.next_states = self._format_status_list(book_obj.get_available_next_states(human_readable=True))
        self.path_to_success = self._format_status_list(book_obj.get_path_to_upload(human_readable=True), separator='->')
        self.identifier = book_obj.identifier or NONE_STR
        self._has_identifier = bool(book_obj.identifier)
        to_string = self._book_value_to_string
        self.leafs = to_string(book_obj, 'leafs')
        self.title = to_string(book_obj, 'title')
        self.creator = to_string(book_obj, 'creator')
        self.volume = to_string(book_obj, 'volume')
        self.boxid = to_string(book_obj, 'boxid')
        self.isbn = to_string(book_obj, 'isbn')
        self.shiptracking = to_string(book_obj, 'shiptracking')
        self.operator = to_string(book_obj, 'operator')
        if book_obj.date_last_modified:
            self.edit_date = time.strftime('%m/%d/%Y %H:%M:%S',
                                           time.localtime(book_obj.date_last_modified))
        else:
            self.edit_date = NONE_STR

        if book_obj.date_last_updated:
            self.update_date = time.strftime('%m/%d/%Y %H:%M:%S',
                                           time.localtime(book_obj.date_last_updated))
        else:
            self.update_date = NONE_STR

        if book_obj.date_created:
            self.create_date = time.strftime('%m/%d/%Y %H:%M:%S',
                                           time.localtime(book_obj.date_created))
        else:
            self.create_date = NONE_STR

        self.image = book_obj.get_cover_image()
        self.worker_log = book_obj.get_log()

    def _format_status_list(self, status_list, separator='|'):
        ret = " {} ".format(separator).join(status_list)
        return text_type(ret)

    def _update_book_options(self):
        menu = self.ids.entry_box
        num_status = UploadStatus[self._book_obj.status].value
        data = BOOK_STATUS_OPTIONS_TABLE.get(num_status, None)
        data = list(data) if data else list()

        advanced_text = 'Show Advanced'
        if self._show_advanced_options:
            advanced_text = 'Hide Advanced'
            data.append({'key': 'show_plan',
                         'text': 'Action Plan',
                         'icon': 'icon_expand_menu.png',
                         'color': 'blue'})
            data.append({'key': 'move_along',
                         'text': 'Move along',
                         'icon': 'ff.png',
                         'color': 'blue'})
        data.append({'key': 'advanced',
                     'text': advanced_text,
                     'icon': 'baseline_play_circle_filled_white_48dp.png',
                     'color': 'gray'})
        data.append({'key': 'cancel',
                     'text': 'Close',
                     'icon': 'close_x.png',
                     'color': 'gray'})
        if self._show_advanced_options:
            data = self._generate_next_actions_buttons() + data
        if len(data) % 2 == 1:
            data.insert(-2, {'key': 'dummy',
                             'disabled': True,
                             'opacity': 0})
        menu.data = data

    def _generate_next_actions_buttons(self):
        out = []
        next_actions = self._book_obj.get_available_next_actions()
        for action in next_actions:
            option = {'key': 'do_action',
                      'text': action,
                      'icon': 'baseline_play_circle_filled_white_48dp.png',
                      'color': 'orange'}
            out.append(option)
        return out

    def _update_from_metadata(self):
        ''' this updates the values of certain self fields
        listed in `augmented_fields`, with the values fetched from
        reading metadata.xml of that book. We shouldn't be doing this
        here, instead relying on all the right information being passed
        to the constructor, which will come when we can pass more structured
        Book objects (2.0-Release branch)
        '''
        try:
            self.metadata = get_metadata(self.book_path)
        except Exception:
            Logger.exception('Failed to get book metadata from path: {}'
                             .format(self.book_path))
            self.metadata = None
        augmented_fields = ['isbn', 'shiptracking']
        if self.metadata:
            for field in augmented_fields:
                if field in self.metadata:
                    setattr(self,
                            field,
                            self._book_value_to_string(self.metadata, field))

    def _update_ppi_from_scandata(self):
        scandata = self._book_obj.get_scandata()
        bookData = scandata.get('bookData', None)
        if bookData:
            ppi = bookData.get('ppi', None)
            if ppi:
                self.ppi = str(ppi)

    def _book_value_to_string(self, md, key):
        value = md.get(key, None)
        if value is not None:
            if isinstance(value, list):
                return '; '.join(value)
            return '%s' % value
        return NONE_STR

    def _on_option_selection(self, menu, selection):
        selected = selection[0]
        if selected['key'] == 'advanced':
            self._show_advanced_options = not self._show_advanced_options
            self._update_book_options()
        elif selected['key'] == 'do_action':
            self.submit_data((selection[0]['key'], selection[0]['text']))
        else:
            self.submit_data(selection[0]['key'])

    def _on_book_event(self, event, book, topic):
        #self._update()
        pass

    def open_book_path(self):
        book_path = self.book_path
        if book_path and exists(book_path):
            subprocess.check_call(['xdg-open', book_path.encode('utf-8')])

    def on_dismiss(self):
        super(BookMenuPopup, self).on_dismiss()
        self.hide_log_panel()
        if self._book_obj:
            self._book_obj.unsub(self._trigger_update)
            self._book_obj = None
        self.book = None

    def show_log_panel(self, log, log_state):
        if not self._log_panel:
            self._log_panel = BookMenuPopupLogPanel(size_hint_y=0.95)
            self._log_panel.fbind('state', self._on_log_panel_state)
        if not self._log_displayed:
            self.ids.container.add_widget(self._log_panel)
            self._log_displayed = True
        self._log_panel.log = log
        self._log_panel.state = log_state

    def hide_log_panel(self):
        if self._log_panel and self._log_displayed:
            self._log_displayed = False
            self._log_panel.state = 'close'
            self.ids.container.remove_widget(self._log_panel)

    def _on_log_panel_state(self, log_panel, state):
        if state == 'close':
            self.hide_log_panel()
        elif state == 'show_log':
            log_panel.log = self.worker_log
        elif state == 'show_full_log':
            log = self._book_obj.get_full_log()
            log_panel.log = log[-10000:]
        elif state == 'show_history':
            history = self._book_obj.get_status_history()
            log_panel.log = '\n'.join(history)

    def show_log(self):
        self.show_log_panel(self.worker_log, 'show_log')

    def show_book_history(self):
        history = self._book_obj.get_status_history()
        self.show_log_panel('\n'.join(history), 'show_history')

    def show_book_full_log(self, *args):
        log = self._book_obj.get_full_log()
        # not entirely sure why truncating is necessary, but for now...
        self.show_log_panel(log[-10000:], 'show_full_log')

    def open_web_identifier(self):
        if self._has_identifier:
            webbrowser.open('https://archive.org/details/{}'
                            .format(self._book_obj.identifier))

    def lock_controls(self):
        self.ids.entry_box.disabled = True

    def unlock_controls(self):
        self.ids.entry_box.disabled = False
