import time
import webbrowser
from functools import partial
from os.path import join, dirname, exists

import regex as re
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.lang import Builder
from kivy.properties import (
    StringProperty,
    BooleanProperty,
    NumericProperty,
    ListProperty,
    OptionProperty,
    ObjectProperty,
)
from kivy.uix.behaviors import CompoundSelectionBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import (
    RecycleDataViewBehavior,
    RecycleDataAdapter
)
from kivy.uix.stencilview import StencilView
from kivy.uix.label import Label
from sortedcontainers import SortedListWithKey

from ia_scribe.scribe_globals import MISSING_IMAGE
from ia_scribe.uix.behaviors.tooltip import TooltipControl, TooltipBehavior
from ia_scribe.uix.components.sort_header import SortHeader
from ia_scribe.book.upload_status import UploadStatus, status_human_readable, ERROR_STATES
from ia_scribe.utils import get_string_value_if_list, get_sorting_value
from ia_scribe.config.config import Scribe3Configuration

Builder.load_file(join(dirname(__file__), 'library_view.kv'))

config = Scribe3Configuration()

NONE_STR = '-'


class BookView(object):

    title = StringProperty(NONE_STR)
    creator = StringProperty(NONE_STR)

    index = NumericProperty(-1)
    selected = BooleanProperty(False)
    color_normal = ListProperty([1, 1, 1, 1])
    color_down = ListProperty([0.2, 0.65, 0.8, 1])

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        self.selected = False
        self.title = get_string_value_if_list(data, 'title') or NONE_STR
        self.creator = get_string_value_if_list(data, 'creator') or NONE_STR
        self.disabled = data.get('processed', False)

    def to_status_string(self, status):
        if status == UploadStatus.packaging_failed.value:
            return 'Packaging error'
        try:
            status_name = UploadStatus(status).name
            return status_human_readable.get(status_name, status_name)
        except ValueError:
            return 'Unknown status'

    def on_touch_down(self, touch):
        if self.disabled and self.collide_point(*touch.pos):
            return True
        if touch.button == 'left' and self.collide_point(*touch.pos):
            touch.grab(self)
            self.selected = True
            return True

    def on_touch_move(self, touch):
        return touch.grab_current is self

    def on_touch_up(self, touch):
        if self.disabled and self.collide_point(*touch.pos):
            if touch.grab_current is self:
                touch.ungrab(self)
            return True
        if touch.grab_current is self and touch.button == 'left':
            touch.ungrab(self)
            parent = self.parent
            if isinstance(parent, CompoundSelectionBehavior):
                if self.collide_point(*touch.pos):
                    parent.select_with_touch(self.index)
                    parent.deselect_node(self.index)
            self.selected = False
            return True

    def apply_selection(self, rv, index, is_selected):
        self.selected = is_selected


class BookViewLabel(TooltipBehavior, Label):
    pass


class BookRowView(TooltipControl, BookView, RecycleDataViewBehavior, BoxLayout):

    media_type = StringProperty('item', allownone=False)
    date = StringProperty(NONE_STR)
    identifier = StringProperty(NONE_STR)
    status = StringProperty(NONE_STR)
    status_color = ListProperty([0, 0, 0, 1])
    status_bold = BooleanProperty(False)
    operator = StringProperty(NONE_STR)
    notes_count = StringProperty(NONE_STR)
    leafs_count = StringProperty(NONE_STR)
    shiptracking_id = StringProperty(NONE_STR)
    date_last_modified = StringProperty(NONE_STR)
    date_created = StringProperty(NONE_STR)

    def __init__(self, **kwargs):
        self._id_exist = self.identifier != NONE_STR and not self.disabled
        super(BookRowView, self).__init__(**kwargs)
        self.use_tooltips = True

    def refresh_view_attrs(self, rv, index, data):
        super(BookRowView, self).refresh_view_attrs(rv, index, data)
        self.media_type = data.get('type').lower()
        self.identifier = data.get('identifier', None) or NONE_STR
        status_code = data.get('status', None)
        if status_code in ERROR_STATES:
            status_color = [1, 0, 0, 1]
            status_bold = True
        else:
            status_color = [0, 0, 0, 1]
            status_bold = False

        if data.get('error', None):
            self.color_normal = [.5, 0, 0, 0.2]
        else:
            self.color_normal = [0, 0, 0, 0]

        self.status = self.to_status_string(status_code)
        msg = data.get('msg', None)
        if msg:
            self.status = "{}".format(msg)
        self.status_color = status_color
        self.status_bold = status_bold
        self.operator = get_string_value_if_list(data, 'operator') or NONE_STR
        self.notes_count = str(data.get('notes_count', 0) or NONE_STR)
        self.leafs_count = str(data.get('leafs', 0) or NONE_STR)
        date = data.get('date', None)
        if date:
            self.date = time.strftime('%m/%d/%Y %H:%M:%S',
                                      time.localtime(date))
        else:
            self.date = NONE_STR
        date_last_modified = data.get('date_last_modified', None)
        if date_last_modified:
            self.date_last_modified = time.strftime('%m/%d/%Y %H:%M:%S',
                                  time.localtime(date_last_modified))
        else:
            self.date_last_modified = NONE_STR

        date_created = data.get('date_created', None)
        if date_created:
            self.date_created = time.strftime('%m/%d/%Y %H:%M:%S',
                                  time.localtime(date_created))
        else:
            self.date_created = NONE_STR

        tracking_field = 'boxid' if config.is_true('show_boxid') else 'shiptracking'
        self.shiptracking_id = \
            get_string_value_if_list(data, tracking_field) or NONE_STR
        self._id_exist = self.identifier != NONE_STR and not self.disabled

    def on_touch_down(self, touch):
        if self._id_exist and self.ids.identifier_button.on_touch_down(touch):
            return True
        return super(BookRowView, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        if self._id_exist and self.ids.identifier_button.on_touch_move(touch):
            return True
        return super(BookRowView, self).on_touch_move(touch)

    def on_touch_up(self, touch):
        if self._id_exist and self.ids.identifier_button.on_touch_up(touch):
            return True
        return super(BookRowView, self).on_touch_up(touch)

    def _on_identifier_button_release(self, button):
        # TODO: Move this to event which LibraryView can dispatch
        if self._id_exist:
            if button.last_touch.button == 'left':
                url = 'https://archive.org/details/{}'.format(self.identifier)
                webbrowser.open(url)
            elif button.last_touch.button == 'right':
                Clipboard.copy(self.identifier)


class BookThumbView(BookView, RecycleDataViewBehavior, BoxLayout):

    image_source = StringProperty(MISSING_IMAGE)
    title = StringProperty(NONE_STR)
    creator = StringProperty(NONE_STR)
    identifier = StringProperty(None, allownone=True)

    def refresh_view_attrs(self, rv, index, data):
        super(BookThumbView, self).refresh_view_attrs(rv, index, data)
        book_path = data.get('path', None)
        if book_path:
            thumb_path = join(data['path'], 'thumbnails', '0001.jpg')
            image_source = thumb_path if exists(thumb_path) else MISSING_IMAGE
        else:
            image_source = MISSING_IMAGE
        self.image_source = image_source
        self.identifier = data.get('identifier', None)


class BookViewContainer(LayoutSelectionBehavior, RecycleGridLayout):

    def get_index_of_node(self, node, selectable_nodes):
        return node

    def compute_sizes_from_data(self, data, flags):
        self._selectable_nodes = list(range(len(data)))
        res = RecycleGridLayout.compute_sizes_from_data(self, data, flags)
        return res

class BookSortHeader(SortHeader):
    tracking = StringProperty('Shiptracking')
    views_layout = OptionProperty('list', options=['list', 'grid'])

    def __init__(self, **kwargs):
        if config.is_true('show_boxid'):
            self.tracking = 'Boxid'
        super(BookSortHeader, self).__init__(**kwargs)


class LibraryViewHeader(TooltipControl, BoxLayout, StencilView):

    EVENT_OPTION_SELECT = 'on_option_select'
    OPTION_NEW_BOOK = 'new_book'
    OPTION_NEW_CD = 'new_cd'
    OPTION_WIZARD = 'wizard'
    OPTION_IMPORT_BOOK = 'import_book'

    filter_text = StringProperty()
    views_layout = OptionProperty('list', options=['list', 'grid'])
    filter_status = NumericProperty(0)
    book_statuses = ObjectProperty(set(), baseclass=set)

    _internal = False
    '''True if _on_view_menu_button_state is setting `views_layout` attribute.
    '''

    __events__ = (EVENT_OPTION_SELECT,)

    def __init__(self, **kwargs):
        self._internal = False
        super(LibraryViewHeader, self).__init__(**kwargs)
        Clock.schedule_once(self._postponed_init, -1)

    def _postponed_init(self, *args):
        for button in self.ids.view_menu.children:
            button.fbind('state', self._on_view_menu_button_state)
            if button.state == 'down':
                self._on_view_menu_button_state(button, button.state)

    def _on_view_menu_button_state(self, button, state):
        if state == 'down':
            self._internal = True
            self.views_layout = button.key
            self._internal = False
    
    def on_book_statuses(self, header, book_statuses):
        if self.filter_status != 0 or self.filter_status not in book_statuses:
            self.filter_status = 0
            self.ids.filter_spinner.text = 'all'
        spinner_values = ['all']
        for status_code in book_statuses:
            spinner_values.append(UploadStatus(status_code).name)
        self.ids.filter_spinner.values[:] = spinner_values
    
    def _on_filter_spinner_value(self, spinner, status):
        # This is where we actually convert literals to numbers
        self.filter_status = UploadStatus[status].value if status != 'all' else 0

    def on_views_layout(self, header, views_layout):
        if self._internal:
            return
        for button in self.ids.view_menu.children:
            if button.key == views_layout:
                button.trigger_action(0)

    def on_option_select(self, option):
        pass


class BooksDataAdapter(RecycleDataAdapter):

    view_spacing = NumericProperty()

    def create_view(self, index, data_item, viewclass):
        view = super(BooksDataAdapter, self).create_view(
            index, data_item, viewclass
        )
        if isinstance(view, BookRowView):
            view.spacing = self.view_spacing
        return view

    def on_view_spacing(self, adapter, spacing):
        for view in self.dirty_views[BookRowView]:
            view.spacing = spacing
        if BookRowView in self.views:
            for view in self.views[BookRowView]:
                view.spacing = spacing


class LibraryView(GridLayout):

    EVENT_BOOK_SELECT = 'on_book_select'
    NUMBER_KEYS = {'status', 'notes_count', 'leafs'}

    books = ListProperty()
    sort_key = StringProperty('date_last_modified')
    sort_order = StringProperty('desc')
    filter_text = StringProperty()
    views_layout = OptionProperty('list', options=['list', 'grid'])
    views_spacing = NumericProperty('5dp')
    filter_status = NumericProperty()

    __events__ = (EVENT_BOOK_SELECT,)

    def __init__(self, **kwargs):
        self._temp_filter_text = ''
        self._filter_trigger = \
            Clock.create_trigger(self._do_filtering, 0.3)
        self._sort_trigger = \
            Clock.create_trigger(self._do_sorting)
        self.fbind('sort_key', self.on_sort_key_and_sort_order)
        self.fbind('sort_order', self.on_sort_key_and_sort_order)
        self.fbind('filter_status', self._filter_trigger)
        views_layout = kwargs.pop('views_layout', None)
        super(LibraryView, self).__init__(**kwargs)
        if views_layout is not None:
            kwargs['views_layout'] = views_layout
        Clock.schedule_once(partial(self._postponed_init, **kwargs), -1)

    def _postponed_init(self, dt, **kwargs):
        view_adapter = BooksDataAdapter(view_spacing=self.views_spacing)
        self.fbind('views_spacing', view_adapter.setter('view_spacing'))
        rv = self.ids.rv
        rv.view_adapter = view_adapter
        rv.layout_manager.fbind('selected_nodes', self.on_selected_indices)
        self.views_layout = kwargs.get('views_layout', self.views_layout)
        if 'views_layout' not in kwargs:
            self.on_views_layout(self, self.views_layout)

    def update_book(self, uuid, record):
        if uuid is None:
            return
        download_incomplete = UploadStatus.download_incomplete.value
        for index, book in enumerate(self.books):
            if book.get('uuid', None) == uuid:
                book.update(record)
                self.ids.rv.refresh_from_data()
                return

    def find_by_uuid(self, uuid):
        if uuid is None:
            return None
        for book in self.books:
            if book.get('uuid', None) == uuid:
                return book
        return None

    def refresh_views(self, *args):
        self.ids.rv.refresh_from_data()

    def on_books(self, view, books):
        filtered_books = self._filter_and_sort()
        # populate the list of available statuses for Header spinner
        statuses = set(x['status'] for x in filtered_books)
        self.ids.library_header.book_statuses = statuses
        self._update_rv_data(filtered_books)

    def on_sort_key_and_sort_order(self, *args):
        if not self._sort_trigger.is_triggered:
            self._sort_trigger()

    def on_filter_text(self, filter_input, text):
        if not self._filter_trigger.is_triggered \
                and self._temp_filter_text != text:
            self._temp_filter_text = text
            self._filter_trigger()

    def _filter_and_sort(self):
        filter_status = self.filter_status
        get = get_string_value_if_list
        if filter_status == 0 and not self.filter_text:
            return sorted(
                self.books,
                key=self._get_sorting_value,
                reverse=self.sort_order == 'desc'
            )
        matched = SortedListWithKey(key=self._get_sorting_value)
        if filter_status and not self.filter_text:
            for book in self.books:
                if self.filter_status == get(book, 'status'):
                    matched.add(book)
            return reversed(matched) if self.sort_order == 'desc' else matched
        pattern = re.compile(re.escape(self.filter_text),
                             re.IGNORECASE | re.UNICODE)
        for book in self.books:
            title = get(book, 'title') or ''
            creator = get(book, 'creator') or ''
            identifier = get(book, 'identifier') or ''
            shiptracking_id = get(book, 'shiptracking') or ''
            status = get(book, 'status')
            if (pattern.search(title)
                or pattern.search(creator)
                or pattern.search(identifier)
                or pattern.search(shiptracking_id)):
                if filter_status != 0:
                    if filter_status == status:
                        matched.add(book)
                else:
                    matched.add(book)
        return reversed(matched) if self.sort_order == 'desc' else matched

    def _do_sorting(self, *args):
        # Called by trigger
        books = sorted(
            self.ids.rv.data,
            key=self._get_sorting_value,
            reverse=self.sort_order == 'desc'
        )
        self._update_rv_data(books)

    def _do_filtering(self, *args):
        # Called by trigger
        text = self.ids.library_header.ids.filter_input.text
        if self._temp_filter_text == text:
            books = self._filter_and_sort()
            self._update_rv_data(books)
        else:
            self._temp_filter_text = text
            self._filter_trigger()

    def _update_rv_data(self, books):
        rv = self.ids.rv
        rv.layout_manager.clear_selection()
        rv.data = books
        rv.scroll_y = 1.0

    def _get_sorting_value(self, book):
        key = self.sort_key
        value = get_string_value_if_list(book, key)
        return get_sorting_value(value, key,
                                 number_keys=self.NUMBER_KEYS,
                                 default_value='')

    def on_views_layout(self, library_view, views_layout):
        rv = self.ids.rv
        if views_layout == 'grid':
            Builder.unbind_widget(rv.layout_manager.uid)
            Builder.apply_rules(rv.layout_manager,
                                'BookThumbViewContainer')
            rv.viewclass = BookThumbView
            rv.layout_manager.spacing = self.views_spacing
        elif views_layout == 'list':
            Builder.unbind_widget(rv.layout_manager.uid)
            Builder.apply_rules(rv.layout_manager, 'BookRowViewContainer')
            rv.viewclass = BookRowView
            rv.layout_manager.spacing = 0

    def on_selected_indices(self, layout_manager, selected_indices):
        if selected_indices:
            book = self.ids.rv.data[selected_indices[0]]
            self.dispatch(self.EVENT_BOOK_SELECT, book)

    def on_book_select(self, book):
        pass
