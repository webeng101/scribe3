import subprocess
import re
from collections import Counter
from functools import partial
from os.path import join, dirname, exists

from isbnlib import notisbn
from kivy.app import App
from kivy.clock import Clock
from kivy.compat import text_type
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.metrics import dp
from kivy.properties import (
    StringProperty,
    NumericProperty,
    BooleanProperty,
    ObjectProperty,
    ListProperty,
    DictProperty,
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from ia_scribe.uix.behaviors.tooltip import TooltipBehavior, TooltipControl
from kivy.uix.screenmanager import Screen
from kivy.uix.image import Image

from ia_scribe.book.book import (
    ST_DOWNLOADED,
    ST_PRELOADED,
    ST_HAS_MARC_BIN,
    ST_HAS_MARC_XML,
    ST_HAS_METASOURCE,
    ST_QUEUED_FOR_DELETE,
    ST_MARC_DOWNLOAD_FAILED
)
from ia_scribe.book.metadata import (
    is_valid_issn,
    MD_ACRONYMS,
    MD_KEYS_WITH_SINGLE_VALUE,
    MD_READONLY_KEYS
)
from ia_scribe.uix.actions.generic import ColoredYesNoActionPopupMixin
from ia_scribe.uix.actions.info import ShowGenericInfoAction
from ia_scribe.uix.behaviors.form import FormBehavior
from ia_scribe.uix.behaviors.tooltip import TooltipScreen
from ia_scribe.uix.widgets.marc.MARC import MARCPopup
from ia_scribe.uix.widgets.wonderfetch.wonderfetch_widget import WonderfetchDialog
from ia_scribe.uix.components.labels.labels import BlackLabel
from ia_scribe.uix.components.poppers.popups import (
    InfoPopup,
    QuestionPopup,
    NewMetadataFieldPopup,
    UniversalIDPopup,
    ProgressPopup,
    RejectBookPopup,
)
from ia_scribe.uix_backends.book_metadata_screen_backend import \
    BookMetadataScreenBackend
from ia_scribe.uix.actions.error import ShowErrorAction

from ia_scribe.config.config import Scribe3Configuration
config = Scribe3Configuration()
from ia_scribe.utils import get_scanner_property

Builder.load_file(join(dirname(__file__), 'book_metadata_screen.kv'))

# Keys that should not be displayed in metadata form
MD_SKIP_KEYS = {'collection', 'collection_set', 'catalog', 'camera', 'ppi',
                'identifier', 'boxid', 'old_pallet', 'volume', 'rcs_key',}
# Keys that are displayed on an empty, new book
MD_BASIC_KEYS = {'title', 'creator', 'language', 'date', 'isbn', 'publisher',}
# Keys that aren't set from the MD form
MD_IGNORE_FORM = {'sponsor', 'contributor', 'partner'}

class BookMetadataItem(RecycleDataViewBehavior, BoxLayout):

    index = NumericProperty()
    key = StringProperty()
    text = StringProperty()
    readonly = BooleanProperty(False)

    message = StringProperty()
    focus = BooleanProperty(False)
    use_delete_button = BooleanProperty(True)

    __events__ = ('on_delete',)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        self.focus = False
        self.key = self._format_key(data['key'])
        self.readonly = readonly = data.get('readonly', False)
        self.text = text_type(data['value'])
        self.use_delete_button = not (data.get('required', False) or readonly)
        self.disabled = rv.layout_manager.disabled
        self.validate(data)

    def validate(self, data):
        self.message = ''
        if not data.get('new_book', False) and not data.get('valid', True):
            self.message = data.get('message', '')

    def _format_key(self, key):
        if key in MD_ACRONYMS:
            return u'{}:'.format(key.upper())
        return u'{}:'.format(key.capitalize())

    def _on_delete_button_release(self, *args):
        self.dispatch('on_delete')

    def on_delete(self):
        pass


class SeparatorLabelItem(RecycleDataViewBehavior, BlackLabel):

    _default_color = [0, 0, 0, 1]

    def refresh_view_attrs(self, rv, index, data):
        self.text = data.get('text', u'')
        self.color = data.get('color', self._default_color)
        self.disabled_color = self.color


class BookMetadataLayout(RecycleGridLayout):

    __events__ = ('on_view_added', 'on_view_removed')

    def add_widget(self, widget, index=0):
        super(BookMetadataLayout, self).add_widget(widget, index)
        self.dispatch('on_view_added', widget)

    def remove_widget(self, widget):
        super(BookMetadataLayout, self).remove_widget(widget)
        self.dispatch('on_view_removed', widget)

    def on_view_added(self, view):
        pass

    def on_view_removed(self, view):
        pass


class BookMetadataView(FormBehavior, RecycleView):

    use_basic_view = BooleanProperty(True)

    def __init__(self, **kwargs):
        self.deleted_data = []
        self.all_data = []
        self.all_data_keys = Counter()
        self.fbind('use_basic_view', self._do_filtering)
        super(BookMetadataView, self).__init__(**kwargs)

    def set_data(self, data):
        del self.deleted_data[:]
        self.all_data_keys = Counter(x['key'] for x in data if 'key' in x)
        self.all_data = data
        self._do_filtering()

    def add_item(self, item):
        self.all_data_keys[item['key']] += 1
        self.all_data.append(item)
        self._do_filtering()
        self.scroll_y = 0.0

    def collect_data(self):
        # Collect non-readonly items
        metadata = []
        for item in self.all_data:
            if 'view_class' not in item:
                # It's a default view_class == BookMetadataItem
                if not item['key'] in MD_IGNORE_FORM:
                    metadata.append(item)
        metadata.extend(self.deleted_data)
        return metadata

    def validate(self, *args):
        view_class = self.layout_manager.key_viewclass
        for item in self.all_data:
            if not item.get('deleted', False) and view_class not in item:
                self.validate_item(item)
                item.pop('new_book', False)
        self.refresh_from_data()

    def validate_item(self, item):
        key, value = item['key'], item['value']
        item['valid'] = True
        if key == 'isbn' and notisbn(value) \
                or key == 'issn' and not is_valid_issn(value):
            if value == "":
                pass
            else:
                item['valid'] = False
                item['message'] = 'Must be valid {}'.format(key)
        elif key == 'page-progression':
            if value not in ['lr', 'rl']:
                item['valid'] = False
                item['message'] = '{} must be either "rl" or "lr"'.format(key)
        #elif not value:
        #    item['valid'] = False
        #    item['message'] = 'Cannot be empty'

    def on_layout_manager(self, view, layout_manager):
        if layout_manager:
            layout_manager.key_viewclass = 'view_class'
            layout_manager.bind(on_view_added=self._on_view_added,
                                on_view_removed=self._on_view_removed)

    def _on_view_added(self, layout_manager, view):
        if isinstance(view, BookMetadataItem):
            view.fbind('text', self._on_view_text_input)
            view.fbind('on_delete', self._on_view_delete)

    def _on_view_removed(self, layout_manager, view):
        if isinstance(view, BookMetadataItem):
            view.funbind('text', self._on_view_text_input)
            view.funbind('on_delete', self._on_view_delete)

    def _do_filtering(self, *args):
        if self.use_basic_view:
            self.data = filter(
                lambda x: 'key' not in x
                          or (not x.get('deleted', False)
                              and x['key'] in MD_BASIC_KEYS),
                self.all_data
            )
        else:
            self.data = filter(
                lambda x: not x.get('deleted', False),
                self.all_data
            )

    def _on_view_text_input(self, view, text):
        item = self.data[view.index]
        item['value'] = text
        self.validate_item(item)
        view.validate(item)

    def _on_view_delete(self, view):
        item = self.data.pop(view.index)
        item['deleted'] = True
        self.deleted_data.append(item)
        self.all_data_keys[item['key']] -= 1


class BookMetadataScreen(TooltipScreen, TooltipBehavior, Screen):

    books_db = ObjectProperty(allownone=True)
    task_scheduler = ObjectProperty(allownone=True)
    camera_system = ObjectProperty(allownone=True)

    input_disabled = BooleanProperty(False)
    target_extra = ObjectProperty(allownone=True)
    catalogs = ListProperty(['none',])
    collection_sets_mapping = DictProperty()
    formatted_collection_sets = ListProperty()
    is_current_rcs_default = BooleanProperty()
    collection_string = StringProperty()
    current_catalog = StringProperty('none')
    can_reprint_slip = BooleanProperty(False)
    _marc_popup = ObjectProperty(None, allownone=True)
    object_type = StringProperty('item')
    OLD_PALLET_VALIDATION_REGEX = StringProperty()
    BOXID_VALIDATION_REGEX = StringProperty()

    __events__ = ('on_done', 'on_cancel')

    def __init__(self, **kwargs):
        self._search_option = 'identifier'
        self._new_book = False
        self._input_trigger = Clock.create_trigger(self._on_input_disabled, -1)
        self.fbind('disabled', self._input_trigger)
        self.fbind('input_disabled', self._input_trigger)
        self.OLD_PALLET_VALIDATION_REGEX = config.get('old_pallet_validation_regex', '(IA-..-\d{7})|(IA|CH)[\dxX]{4,5}')
        self.BOXID_VALIDATION_REGEX = config.get('boxid_validation_regex', '^IA\d{6,7}$')
        super(BookMetadataScreen, self).__init__(**kwargs)
        self._new_metadata_field_popup = NewMetadataFieldPopup()
        self._progress_popup = ProgressPopup()
        self.backend = BookMetadataScreenBackend(
            task_scheduler=self.task_scheduler
        )
        self._bind_backend_events()
        Clock.schedule_once(self._postponed_init, -1)

    def _postponed_init(self, *args):
        self._setup_new_metadata_field_popup()
        self._wonderfetch_popup = WonderfetchDialog()
        self.catalogs = self._wonderfetch_popup.catalogs
        self.current_catalog = self._wonderfetch_popup.default_catalog
        self._bind_wonderfetch_popup_events()

    def _bind_backend_events(self):
        md_loaded_trigger = Clock.create_trigger(self._on_metadata_loaded, -1)
        bk = self.backend
        bk.fbind(bk.EVENT_INIT, self._on_backend_init)
        bk.fbind(bk.EVENT_INIT, self._input_trigger)
        bk.fbind(bk.EVENT_BOOK_STATE, self._on_book_state)
        bk.fbind(bk.EVENT_ERROR, self._on_error)
        bk.fbind(bk.EVENT_METADATA_ERROR, self._on_metadata_error)
        bk.fbind(bk.EVENT_METADATA_DEFERRED, self._on_metadata_deferred)
        bk.fbind(bk.EVENT_IDENTIFIER_LOADED, self._on_identifier)
        bk.fbind(bk.EVENT_OFFLINE_ITEM_CREATED, self._on_offline_item_created)
        bk.fbind(bk.EVENT_METADATA_LOADED, md_loaded_trigger)
        bk.fbind(bk.EVENT_SELECT_IDENTIFIER, self._on_select_identifier)
        bk.fbind(bk.EVENT_START_MARC, self._on_start_marc)
        bk.fbind(bk.EVENT_TASK_START, self._progress_popup.open)
        bk.fbind(bk.EVENT_TASK_END, self._progress_popup.dismiss)
        bk.fbind(bk.EVENT_TASK_PROGRESS, self._on_task_progress)
        bk.fbind(bk.EVENT_BOOK_REJECTED, self._on_book_rejected)
        bk.fbind(bk.EVENT_START_WONDERFETCH, self._on_start_wonderfetch)
        bk.fbind(bk.EVENT_END_WONDERFETCH_SUCCESS, self._on_wonderfetch_success)
        bk.fbind(bk.EVENT_SLIP_PRINTED, self._on_slip_printed)
        bk.fbind(bk.EVENT_RCS_UPDATED, self._on_rcs_updated)

    def _setup_new_metadata_field_popup(self):
        popup = self._new_metadata_field_popup
        popup.target_widget = self.ids.metadata_form
        popup.fbind('on_submit', self._on_new_metadata_field_popup_submit)

    def _bind_wonderfetch_popup_events(self):
        popup = self._wonderfetch_popup
        popup.fbind(popup.EVENT_CANNOT_SCAN_BOOK, self._on_wonderfetch_cannot_scan_book)
        popup.fbind(popup.EVENT_SCAN_BOOK, self._on_wonderfetch_scan_book)
        popup.fbind(popup.EVENT_REJECT_BOOK, self._on_wonderfetch_reject_book)
        popup.fbind(popup.EVENT_SCAN_EXISTING_BOOK, self._on_wonderfetch_scan_book)
        popup.fbind(popup.EVENT_RETRIEVAL_ERROR, self._on_wonderfetch_retrieval_error)

    def _bind_marc_popup_events(self, popup):
        popup.fbind(popup.EVENT_RECORD_SELECTED,
                    self.on_marc_selected_record)

    def _ensure_book_path_and_init(self, *args):
        if not self.backend.book_path:
            self.backend.create_new_book()
            self.backend.init()

    def start_load_metadata(self, identifier, volume):
        option = self._search_option
        if option == 'identifier':
            self.backend.load_metadata_via_identifier(identifier)
        elif option in ['isbn', 'openlibrary']:
            catalog = self.current_catalog
            if self.is_loading_allowed():
                self.backend.wonderfetch_search(option, identifier, volume, catalog)

    def generate_identifier(self):
        self._save_metadata_if_valid(callback=self.do_generate_identifier)

    def do_generate_identifier(self):
        self.backend.make_identifier()

    def start_print_slip(self, identifier):
        self.action = ColoredYesNoActionPopupMixin(
            action_function=self.actually_reprint_slip,
            title='Reprint slip?',
            message='Are you sure you want to PRINT AGAIN this slip?',
            extra=identifier,
        )
        self.action.display()

    def actually_reprint_slip(self, action, *args, **kwargs):
        identifier = action.extra_args
        self.save_metadata()
        self.backend.generate_and_print_slip(identifier)

    def start_print_slip_and_upload(self, identifier, next_action=None):
        self.save_metadata()
        self.backend.generate_reserve_print_slip(identifier, next_action)

    def start_marc_search(self, identifier):
        self.backend.marc_search(identifier)

    def reject_button_action(self):
        self._save_metadata_if_valid(callback=self.show_book_reject_popup,
                                     force=True, # this suppresses the "insufficient metadata" window
                                     ignore_fields=['old_pallet'])

    def show_book_reject_popup(self):
        popup = RejectBookPopup(title="Reject book",
                                message="Please indicate the rejection reason")
        popup.fbind('on_submit', self._on_reject_book_popup_submit)
        popup.open()

    def _on_reject_book_popup_submit(self, popup, data):
        popup.dismiss()
        self.backend.reject_book(data)

    def show_slip(self, *args):
        if not self.backend.book_obj.has_slip():
            return
        slip_image = Image(source=self.backend.book_obj.get_slip(full_path=True),
                           size_hint=(None, None),
                           allow_stretch=True,
                           )
        slip_image.size = slip_image.texture_size
        slip_name = self.backend.book_obj.get_slip_type()
        self.action = ShowGenericInfoAction(
            additional_content=slip_image,
            title='Slip type #{}'.format(slip_name)
        )
        self.action.display()

    def save_metadata(self):
        Logger.info('BMDS: User pressed Save button')
        self._save_metadata_if_valid()

    def save_metadata_and_done(self):
        Logger.info('BMDS: User pressed Save&Done button')
        self._save_metadata_if_valid(callback=self.done)

    def is_loading_allowed(self):
        if self.backend.is_this_a_supercenter() and not self._ensure_boxid_and_old_pallet():
            self.show_error('You must supply a compliant boxid\n'
                            'value in order to use this feature.')
            return False
        success, md = self.is_metadata_valid()
        # test boxid is not empty here
        return success

    def is_metadata_valid(self, ignore_fields=[]):
        metadata = self.collect_metadata()
        self.ids.metadata_form.validate()
        modern_books_section_ok, payload = self._are_modern_books_items_valid(ignore_fields=ignore_fields)
        if not modern_books_section_ok and self.backend.is_this_a_supercenter():
            self.show_error('Your {} seems to be invalid.'.format(payload['key']))
            return False, None

        identifier_list = list(filter(lambda entry: entry['key'] == 'user_identifier', metadata))
        if len(identifier_list) > 0:
            identifier = identifier_list[0]['value']
            if identifier:
                if not self.is_identifier_valid(identifier):
                    self.show_error('Identifier{} is invalid.'.format(identifier))
                    return False, None
        if self._are_metadata_items_valid(metadata):
            return True, metadata
        else:
            return False, None

    def _save_metadata_if_valid(self, callback=None, force=False, ignore_fields=[]):
        success, metadata = self.is_metadata_valid(ignore_fields=ignore_fields)
        if success:
            self.backend.set_metadata_from_form(metadata)
            self.backend.save_metadata()
            if not self.backend._has_minimum_acceptable_metadata() and not force:
                msg = "Your metadata was saved. However, it appears you are attempting to create an " \
                      "item without some key fields." \
                      "\nAt least [b]title and creator[/b], or [b]isbn[/b] should be present.\n" \
                      "\n[b]Would you like to continue with insufficient metadata?[/b]\n" \
                      "\nClick NO to go back and review the currently available metadata."
                self.show_choice('Insufficient metadata', msg, callback)
                return False
            if callback:
                callback()
            return True
        else:
            self.show_error('Ensure that all fields are non-empty and valid.')
            return False

    def collect_metadata(self):
        md = self.ids.metadata_form.collect_data()
        md.extend(self.collect_global_book_settings())
        if not self.backend.book_obj.is_preloaded():
            md.extend(self.collect_collection())
        md.extend(self.collect_identifier())
        camera = self.backend.get_metadata_item('camera')
        if not camera and self.camera_system:
            camera = self.camera_system.get_name()
            if camera:
                md.append({'key': 'camera', 'value': camera})
        return md

    def _are_metadata_items_valid(self, metadata):
        new_book = self._new_book
        for_removal = []
        for index, item in enumerate(metadata):
            if item.get('deleted', False):
                continue
            value = item['value']
            if not item.get('valid', True):
                return False
        for index, md_index in enumerate(for_removal):
            metadata.pop(md_index - index)
        return True

    def _are_modern_books_items_valid(self, ignore_fields):
        for index, item in enumerate(self.collect_global_book_settings()):
            #if item.get('deleted', False):
            #    continue
            value = item['value']
            if not item.get('valid', True):
                if item['key'] in ignore_fields:
                    continue
                return False, item
        return True, None

    def open_new_metadata_field_popup(self):
        skip_keys = MD_SKIP_KEYS | MD_READONLY_KEYS
        all_data_keys = self.ids.metadata_form.all_data_keys
        for key in all_data_keys:
            if key in MD_KEYS_WITH_SINGLE_VALUE \
                    and all_data_keys[key] == 1:
                skip_keys.add(key)
        self._new_metadata_field_popup.skip_keys = skip_keys
        self._new_metadata_field_popup.open()

    def collect_collection(self):
        collection_set_name = self.ids.collections_spinner.text #will be rcs
        collection_set = self.collection_sets_mapping.get(collection_set_name)
        if collection_set:
            return [
                {'key': 'collection_set', 'value': collection_set.get('name')},
                {'key': 'sponsor', 'value': collection_set.get('sponsor')},
                {'key': 'contributor', 'value': collection_set.get('contributor')},
                {'key': 'partner', 'value': collection_set.get('partner')},
                {'key': 'rcs_key', 'value': u'{}'.format(collection_set.get('rcs_key'))},
                {'key': 'collection',
                 'value': self.backend.create_collections(collection_set.get('name'))}
            ]
        else:
            self.action = ShowErrorAction(
                message='No collection set defined! Saving without collection string information.')
            self.action.display()
            return []

    def add_collection_set(self):
        #Only temporary, use app.get_popup instead
        from ia_scribe.uix.components.poppers.popups import WidgetPopup
        from ia_scribe.uix.widgets.rcs.rcs_widget import RCSSelectionWidget
        self.widget = WidgetPopup(content_class=RCSSelectionWidget,
                                  title='Add new RCS',
                                  size_hint=(None, None),
                                  size=('800dp', '500dp')
                                  )
        self.widget.bind_events({
            'EVENT_CLOSED': self.widget.dismiss,
            'EVENT_RCS_SELECTED': self.backend.add_collection_set,
        })
        self.widget.content.set_center(get_scanner_property('scanningcenter'))
        self.widget.content.fbind(self.widget.content.EVENT_RCS_SELECTED, self._add_collection_set_callback)
        self.widget.open()

    def _add_collection_set_callback(self, *args, **kwargs):
        self.widget.dismiss()

    def is_selection_the_default_collection_set(self, *args, **kwargs):
        spinner_name = self.ids.collections_spinner.text
        selected_rcs = self.collection_sets_mapping.get(spinner_name)
        return selected_rcs == self.backend.rcs_manager.get_default(wrap=False)

    def set_default_collection_set(self, *args, **kwargs):
        spinner_name = self.ids.collections_spinner.text
        selected_rcs = self.collection_sets_mapping[spinner_name]
        if selected_rcs != self.backend.rcs_manager.get_default(wrap=False):
            self.backend.rcs_manager.set_default(selected_rcs)
            self.refresh_collection_star()

    def is_boxid_valid(self, input, old_pallet=False):
        if config.is_true('disable_mandatory_fields_in_dwwi'):
            return True
        res = None

        if old_pallet:
            pattern = self.OLD_PALLET_VALIDATION_REGEX
        else:
            pattern = self.BOXID_VALIDATION_REGEX

        res = re.match(pattern, input)
        if res:
            if len(input) != res.span()[1]:
                res = False
            else:
                res = True
        return res

    def is_identifier_valid(self, identifier):
        pattern = '^[a-zA-Z0-9][a-zA-Z0-9\.\-_]{4,99}$'
        match_result = re.match(pattern, identifier)
        if not match_result:
            return False
        return match_result.string == identifier

    def collect_global_book_settings(self):
        ids = self.ids
        return [
            {'key': 'ppi', 'value': ids.ppi_input.value},
            {'key': 'boxid',
             'value': ids.box_id_input.text,
             'deleted': not ids.box_id_input.text,
             'valid': self.is_boxid_valid(ids.box_id_input.text),},
            {'key': 'old_pallet',
             'value': ids.box_id2_input.text,
             'deleted': not ids.box_id2_input.text,
             'valid': self.is_boxid_valid(ids.box_id2_input.text, old_pallet=True),},
            {'key': 'volume',
             'value': ids.volume_input.text,
             'deleted': not ids.volume_input.text},
        ]

    def collect_identifier(self):
        if self.ids.identifier_input.text:
            return [{'key': 'user_identifier',
                     'value': self.ids.identifier_input.text,}]
        return []

    def reload(self):
        Logger.info('BMDS: User pressed Reload button')
        self.backend.reinit()

    def done(self):
        Logger.info('BMDS: User pressed Done button')
        self.dispatch('on_done')

    def cance_from_user(self):
        Logger.info('BMDS: User pressed Cancel button')
        self.cancel()

    def cancel(self):
        self.dispatch('on_cancel')

    def open_book_path(self):
        book_path = self.backend.book_path
        if book_path and exists(book_path):
            subprocess.check_call(['xdg-open', book_path.encode('utf-8')])

    def show_info(self, message):
        popup = InfoPopup(title='Book metadata information',
                          message=str(message))
        popup.open()

    def show_error(self, message):
        popup = InfoPopup(title='Book metadata error',
                          message=str(message))
        popup.open()

    def show_choice(self, title, message, ok_callback, payload=None):
        popup = QuestionPopup(title=title,
                              message=message,
                              extra={'callback': ok_callback,
                                     'payload': payload},
                              size=(400, 300))
        popup.bind(on_submit=self.ok_callback)
        popup.open()

    def ok_callback(self, popup, option):
        if option == popup.OPTION_YES:
            if 'callback' in popup.extra and popup.extra['callback'] is not None:
                popup.extra['callback']()

    def _on_backend_init(self, backend):
        self._new_metadata_field_popup.dismiss()
        self._progress_popup.dismiss()
        self._on_book_state(backend, backend.get_book_state())
        self._disable_by_state_if_necessary(backend)
        self._on_metadata_loaded(backend)
        self.object_type = self.backend.book_obj.get_type().lower()

    def _on_slip_printed(self, *args):
        ids = self.ids
        ids.slip_present_label.text = 'Yes' if self.backend.book_obj.has_slip() else 'No'
        ids.display_slip_button.opacity = 1 if self.backend.book_obj.has_slip() else 0

    def _on_book_state(self, backend, state):
        self._on_slip_printed()
        ids = self.ids
        ids.marc_xml_label.text = 'Yes' if state & ST_HAS_MARC_XML else 'No'
        ids.marc_bin_label.text = 'Yes' if state & ST_HAS_MARC_BIN else 'No'
        ids.metasource_label.text = \
            'Yes' if state & ST_HAS_METASOURCE else 'No'
        ids.dwwi_and_marc_panel.disabled = bool(state & ST_PRELOADED)
        if state != 0:
            self.input_disabled = (bool(state & ST_DOWNLOADED)
                                   or not bool(state & ST_MARC_DOWNLOAD_FAILED))
        else:
            self.input_disabled = False
        if state & ST_QUEUED_FOR_DELETE:
            Logger.info('BMDS: Cancelling screen because book is flagged for '
                        'deletion')
            self.cancel()

    def _disable_by_state_if_necessary(self, backend):
        if backend.book_obj.status in ['loading_deferred']:
            self.input_disabled = True

    def _on_metadata_loaded(self, *args):
        backend = self.backend
        if not backend.is_initialized():
            return
        self._new_book = not exists(backend.book_path)
        md = backend.create_form_metadata(MD_SKIP_KEYS)
        self._insert_separators_to_metadata(md)
        ids = self.ids
        ids.metadata_form.set_data(md)
        ids.ppi_input.value = backend.book_obj.scandata.get_bookdata('ppi')
        ids.box_id_input.text = backend.get_metadata_item('boxid') or u''
        ids.box_id2_input.text = backend.get_metadata_item('old_pallet') or u''
        ids.volume_input.text = backend.get_metadata_item('volume') or u''
        ids.path_label.text = backend.book_path or ''
        self._populate_collection_sets()
        self.can_reprint_slip = self.backend.can_reprint_slip()

    def _populate_collection_sets(self):
        ret = {}
        default_collection_set = None
        for entry in self.backend.rcs_manager.as_list():
            name_human_readable = '{} ({})'.format(entry.get('name'),
                                                   entry.get('partner'))
            ret[name_human_readable] = entry
            if entry.get('default') is True:
                default_collection_set = name_human_readable
        self.collection_sets_mapping = ret
        self.formatted_collection_sets = ret.keys()

        # select correct entry
        book_metadata = self.backend.get_metadata()
        if 'rcs_key' in book_metadata:
            actual_collection = [human_name for human_name, entry
                                 in self.collection_sets_mapping.items()
                                 if str(entry.get('rcs_key')) ==
                                 str(book_metadata.get('rcs_key'))]
            if len(actual_collection) > 0:
                self.ids.collections_spinner.text = actual_collection[0]
        elif 'collection_set' in book_metadata:
            # If a 'collection set' entry is present, try and match
            actual_collection = [human_name for human_name, entry
                                 in self.collection_sets_mapping.items()
                                 if entry.get('name') == book_metadata.get('collection_set')]
            if len(actual_collection) > 0:
                self.ids.collections_spinner.text = actual_collection[0]
        elif default_collection_set:
            self.ids.collections_spinner.text = default_collection_set

        self.refresh_collection_star()

    def refresh_collection_star(self):
        self.is_current_rcs_default = self.is_selection_the_default_collection_set()
        self.refresh_collection_string()

    def refresh_collection_string(self):
        spinner_name = self.ids.collections_spinner.text
        selected_rcs = self.collection_sets_mapping.get(spinner_name, {})
        self.collection_string = selected_rcs.get('collections', '')

    def _insert_separators_to_metadata(self, metadata):
        separator = {'view_class': 'SeparatorLabelItem',
                     'size': (None, dp(30))}
        last_required_item_index = -1
        for index, item in enumerate(metadata):
            if 'required' in item:
                last_required_item_index = index
        if 0 < last_required_item_index < len(metadata) - 1:
            metadata.insert(last_required_item_index + 1, separator)

    def _on_identifier(self, backend, identifier, *args, **kwargs):
        self.ids.identifier_input.text = identifier or u''
        #self.input_disabled = bool(identifier)

    def _on_new_metadata_field_popup_submit(self, popup, data):
        self.ids.metadata_form.add_item(data)

    def _ensure_boxid_and_old_pallet(self):
        gbs = self.collect_global_book_settings()
        MANDATORY_FIELDS = ['boxid',]
        for item in gbs:
            if item['key'] in MANDATORY_FIELDS:
                if 'valid' in item and not item['valid']:
                    return False
        return True

    def _on_start_marc(self, backend, identifier):
        self._ensure_book_path_and_init()
        app = App.get_running_app()
        marc_popup = app.get_popup(MARCPopup, size=(1200, 700), size_hint=(None, None))
        self._bind_marc_popup_events(marc_popup)
        marc_popup.open()

    def _on_start_wonderfetch(self, backend, method, identifier, volume=None, catalog=None):
        self._ensure_book_path_and_init()
        self._wonderfetch_popup.book_dir = backend.book_path
        old_pallet = self.ids.box_id2_input.text
        if identifier:
            self._wonderfetch_popup.open_search(method, identifier, volume, catalog, old_pallet)
        else:
            self._wonderfetch_popup.open()

    def _on_task_progress(self, backend, report):
        self._progress_popup.message = report.get('message', None) or ''
        self._progress_popup.progress = report.get('progress', 0)

    def _on_error(self, backend, error_message):
        self.show_error(error_message)

    def _on_metadata_error(self, backend, identifier):
        message = (
            'show_create_confirm: Cannot verify item with archive.org\n'
            'Would you like to create the item\n[b]{id}[/b] locally?'
                .format(id=identifier)
        )
        popup = QuestionPopup(title='Offline mode',
                              message=message,
                              extra={'identifier': identifier})
        popup.bind(on_submit=self._on_create_offline_item_popup_submit)
        popup.open()

    def _on_metadata_deferred(self, *args, **kwargs):
        self.done()

    def _on_create_offline_item_popup_submit(self, popup, option):
        if option == popup.OPTION_YES:
            self.backend.create_offline_item(popup.extra['identifier'])

    def _on_offline_item_created(self, backend):
        popup = InfoPopup(
            title='Offline mode',
            message=('Ok, created {} successfully!'
                     .format(backend.get_identifier())),
        )
        popup.open()

    def _on_select_identifier(self, backend, identifiers):
        popup = UniversalIDPopup(identifiers=identifiers)
        popup.fbind('on_submit', self._on_universal_id_popup_submit)
        popup.open()

    def _on_universal_id_popup_submit(self, popup, identifier):
        self.backend.load_metadata_via_identifier(identifier)

    def _on_wonderfetch_scan_book(self, dwwi_popup, payload, search_id, volume, *args):
        if payload:
            extra = self.collect_global_book_settings()
            self.backend.load_metadata_via_openlibrary(payload, extra, search_id, volume)

    def _on_wonderfetch_cannot_scan_book(self, dwwi_widget, catalog, search_key, response):
        self._save_metadata_if_valid(force=True)
        if search_key:
            self.backend.cannot_scan_book(catalog, search_key, response)

    def _on_wonderfetch_reject_book(self, dwwi_popup, isbn, volume, *args):
        self._save_metadata_if_valid(force=True)

    def _on_wonderfetch_success(self, *args, **kwargs):
        self.save_metadata()

    def _on_wonderfetch_retrieval_error(self, popup, error, wid, method, catalog):
        popup.dismiss()
        msg = '[b]We are currently unable to retrieve\nthe metadata for this book.[/b]\n\n' \
              'This could be due to a local or archive.org network issue. ' \
              'You can defer the retrieval to begin shooting the ' \
              'book right now and retry fetching the metadata later.' \
              '\n\n[b]Do you want to defer retrieving ' \
              'metadata and continue to scanning[/b].'

        # prolly wanna use a local method to dismiss, alert and stuff
        ok_callback = partial(self.backend.on_end_wonderfetch_failure,
                              error, wid, method, catalog)
        self.show_choice(title='Defer metadata retrieval?', message=msg,
                         ok_callback=ok_callback)

    def on_marc_selected_record(self, widget, query, data):
        formatted_value = lambda v: v.encode('utf-8').decode('utf-8').encode('ascii', 'ignore') \
                                    if v is not None else 'unknown'
        title = formatted_value(data['dc_meta']['metadata'].get('title', 'title unknown'))
        author = formatted_value(data['dc_meta']['metadata'].get('creator', 'creator unknown'))
        date = formatted_value(data['dc_meta']['metadata'].get('year', 'year unknown'))
        msg = 'Would you like to load metadata for ' \
              '[b]{title}[/b] by [b]{author}[b] ({date})?'.format(
                title=title,
                author=author,
                date=date,
                )
        ok_callback = partial(self._on_marc_record_confirmation,
                              marc_widget=widget, query=query, data=data)
        self.show_choice('Load this MARC?',
                         msg, ok_callback=ok_callback)

    def _on_marc_record_confirmation(self, marc_widget, query, data):
        marc_widget.close()
        self.backend.extract_metadata_from_marc_search(query, data)

    def _on_marc_downloaded_metadata(self, marc_popup, metadata, *args):
        # TODO: Validate downloaded metadata
        self.backend.set_metadata(metadata)
        self.backend.save_metadata()
        self.backend.reinit()

    def _on_input_disabled(self, *args):
        ids = self.ids
        if self.disabled or not self.backend.is_initialized():
            return
        disabled = self.input_disabled
        ids.preloaded_panel.disabled = disabled
        ids.dwwi_and_marc_panel.disabled = disabled
        ids.metadata_form.layout_manager.disabled = disabled
        ids.add_new_field_button.disabled = disabled
        if not disabled:
            # It's possible that all views did not set disabled to False,
            # and therefore we have to refresh the form when disabled is False
            ids.metadata_form.refresh_from_layout()

    def _on_book_rejected(self, *args, **kwargs):
        self.target_extra = None
        if self._progress_popup:
            self._progress_popup.dismiss()
        self.cancel()

    def on_pre_enter(self, *args):
        self.ids.preloaded_id_input.text = u''
        self.ids.identifier_input.text = u''
        extra = self.target_extra
        if extra and extra.get('should_create_new_book', False):
            self.backend.create_new_book()
        self.backend.init()

    def on_leave(self, *args):
        if self._progress_popup:
            self._progress_popup.dismiss()
        self.target_extra = None
        self.backend.reset()
        self.backend.book_path = None

    def on_books_db(self, screen, books_db):
        self.backend.books_db = books_db

    def on_task_scheduler(self, screen, task_scheduler):
        self.backend.task_scheduler = task_scheduler

    def on_done(self):
        pass

    def on_cancel(self):
        pass

    def on_catalogs(self, *args, **kwargs):
        self.ids.catalog_spinner.values[:] = self.catalogs
        if self.current_catalog == 'none':
            self.ids.catalog_spinner.text = self._wonderfetch_popup.default_catalog

    def _on_rcs_updated(self, *args, **kwargs):
        self._populate_collection_sets()
