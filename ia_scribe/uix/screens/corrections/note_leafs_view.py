from os.path import join, dirname
from functools import partial

from kivy.cache import Cache
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import (
    ListProperty,
    NumericProperty,
    StringProperty,
    BooleanProperty
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

from ia_scribe.scribe_globals import MISSING_IMAGE
from ia_scribe.uix.components.sort_header import SortHeader
from ia_scribe.utils import get_sorting_value

Builder.load_file(join(dirname(__file__), 'note_leafs_view.kv'))


class NoteLeafsHeader(SortHeader):
    pass


class NoteLeafsContainer(LayoutSelectionBehavior, RecycleGridLayout):

    def get_index_of_node(self, node, selectable_nodes):
        return node

    def compute_sizes_from_data(self, data, flags):
        self._selectable_nodes = list(range(len(data)))
        return RecycleGridLayout.compute_sizes_from_data(self, data, flags)


class NoteLeafRow(RecycleDataViewBehavior, BoxLayout):

    original_image = StringProperty()
    reshoot_image = StringProperty()
    page_number = StringProperty()
    leaf_number = StringProperty()
    page_type = StringProperty()
    note = StringProperty()
    status_image = StringProperty()

    index = NumericProperty()
    selected = BooleanProperty(False)
    color_normal = ListProperty([1, 1, 1, 1])
    color_down = ListProperty([0.2, 0.65, 0.8, 1])

    def __init__(self, **kwargs):
        self._status_images = {
            0: 'icon_reshoot_32.png',
            1: 'icon_mark_check_32.png'
        }
        super(NoteLeafRow, self).__init__(**kwargs)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        status = data['status']
        self.original_image = data.get('original_image', None) or MISSING_IMAGE
        reshoot_image = MISSING_IMAGE
        if status == 1:
            reshoot_image = data.get('reshoot_image', None) or MISSING_IMAGE
        if reshoot_image != MISSING_IMAGE:
            Cache.remove('kv.loader', reshoot_image)
        self.reshoot_image = reshoot_image
        self.page_number = str(data.get('page_number', None) or '-')
        self.leaf_number = str(data.get('leaf_number', None) or '-')
        self.page_type = data.get('page_type', None) or '-'
        self.note = data.get('note', None) or '-'
        self.status_image = self._status_images.get(status, MISSING_IMAGE)

    def on_touch_down(self, touch):
        if touch.button == 'left' and self.collide_point(*touch.pos):
            touch.grab(self)
            self.selected = True
            return True

    def on_touch_move(self, touch):
        return touch.grab_current is self

    def on_touch_up(self, touch):
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


class NoteLeafsAdapter(RecycleDataAdapter):

    view_spacing = NumericProperty()

    def create_view(self, index, data_item, viewclass):
        view = super(NoteLeafsAdapter, self).create_view(
            index, data_item, viewclass
        )
        if isinstance(view, NoteLeafRow):
            view.spacing = self.view_spacing
        return view

    def on_view_spacing(self, adapter, spacing):
        for view in self.dirty_views[NoteLeafRow]:
            view.spacing = spacing
        if NoteLeafRow in self.views:
            for view in self.views[NoteLeafRow]:
                view.spacing = spacing


class NoteLeafsView(GridLayout):

    EVENT_LEAF_SELECT = 'on_leaf_select'
    NUMBER_KEYS = {'leaf_number', 'page_number', 'status'}

    leafs = ListProperty()
    sort_key = StringProperty('leaf_number')
    sort_order = StringProperty('asc')
    views_spacing = NumericProperty('5dp')

    __events__ = (EVENT_LEAF_SELECT,)

    def __init__(self, **kwargs):
        self._sort_trigger = sort_trigger = \
            Clock.create_trigger(self._do_sorting)
        self.fbind('sort_key', sort_trigger)
        self.fbind('sort_order', sort_trigger)
        super(NoteLeafsView, self).__init__(**kwargs)
        Clock.schedule_once(partial(self._postponed_init, **kwargs))

    def _postponed_init(self, dt, **kwargs):
        view_adapter = NoteLeafsAdapter(view_spacing=self.views_spacing)
        self.fbind('views_spacing', view_adapter.setter('view_spacing'))
        rv = self.ids.rv
        rv.view_adapter = view_adapter
        rv.layout_manager.fbind('selected_nodes', self.on_selected_indices)

    def refresh_views(self, *args):
        self.ids.rv.refresh_from_data()

    def _do_sorting(self, *args):
        # Called by trigger
        key = self.sort_key
        leaves = sorted(
            self.ids.rv.data,
            key=self._get_sorting_value,
            reverse=self.sort_order == 'desc'
        )
        self._update_rv_data(leaves)

    def _update_rv_data(self, leafs):
        rv = self.ids.rv
        rv.layout_manager.clear_selection()
        rv.data = leafs
        rv.scroll_y = 1.0

    def _get_sorting_value(self, item):
        key = self.sort_key
        return get_sorting_value(item.get(key, None),
                                 key,
                                 number_keys=self.NUMBER_KEYS,
                                 default_value='')

    def on_leafs(self, view, leaves):
        sorted_leaves = sorted(
            leaves,
            key=self._get_sorting_value,
            reverse=self.sort_order == 'desc'
        )
        self._update_rv_data(sorted_leaves)

    def on_selected_indices(self, layout_manager, selected_indices):
        if selected_indices:
            note_leaf = self.ids.rv.data[selected_indices[0]]
            self.dispatch(self.EVENT_LEAF_SELECT, note_leaf)

    def on_leaf_select(self, leaf):
        pass
