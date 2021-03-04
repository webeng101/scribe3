from os.path import join, dirname
from functools import partial
import webbrowser

from kivy.compat import  text_type
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import (
    ListProperty,
    NumericProperty,
    StringProperty,
    BooleanProperty,
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

from ia_scribe.scribe_globals import MISSING_IMAGE

Builder.load_file(join(dirname(__file__), 'simple_list.kv'))


class SimpleListContainer(LayoutSelectionBehavior, RecycleGridLayout):

    def get_index_of_node(self, node, selectable_nodes):
        return node

    def compute_sizes_from_data(self, data, flags):
        self._selectable_nodes = list(range(len(data)))
        return RecycleGridLayout.compute_sizes_from_data(self, data, flags)


class SimpleListRow(RecycleDataViewBehavior, BoxLayout):

    image = StringProperty('')
    key = StringProperty()
    value = StringProperty()

    index = NumericProperty()
    selected = BooleanProperty(False)
    color_normal = ListProperty([1, 1, 1, 0])
    color_down = ListProperty([0.2, 0.65, 0.8, 1])

    def __init__(self, **kwargs):
        super(SimpleListRow, self).__init__(**kwargs)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        self.image = data.get('image', None) or MISSING_IMAGE
        self.key = text_type(data.get('key', None) or '-')
        self.value = self.format_value(data.get('value', None))

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

    def format_value(self, value):
        ret = ''
        if type(value) is list:
            ret = ' | '.join(value)
        elif type(value) is dict:
            for n,item in enumerate(iter(sorted(value.items()))):
                k, v = item
                separator = ' | ' if n != 0 else ''
                formatted_key = text_type(k)
                formatted_value = text_type(v)
                item_string = separator + '[size=16][i][b]{k}: [/b][/i][/size][size=18]{v}[/size]'.format(k=formatted_key, v=formatted_value)
                ret += item_string

        else:
            ret = text_type(value)
        return ret


class NoteLeafsAdapter(RecycleDataAdapter):

    view_spacing = NumericProperty()

    def create_view(self, index, data_item, viewclass):
        view = super(NoteLeafsAdapter, self).create_view(
            index, data_item, viewclass
        )
        if isinstance(view, SimpleListRow):
            view.spacing = self.view_spacing
        return view

    def on_view_spacing(self, adapter, spacing):
        for view in self.dirty_views[SimpleListRow]:
            view.spacing = spacing
        if SimpleListRow in self.views:
            for view in self.views[SimpleListRow]:
                view.spacing = spacing


class SimpleList(GridLayout):
    EVENT_LEAF_SELECT = 'on_leaf_select'

    callback = ObjectProperty(None)
    leafs = ListProperty()
    views_spacing = NumericProperty('5dp')
    __events__ = (EVENT_LEAF_SELECT,)

    def __init__(self, **kwargs):
        super(SimpleList, self).__init__(**kwargs)
        Clock.schedule_once(partial(self._postponed_init, **kwargs))

    def _postponed_init(self, dt, **kwargs):
        view_adapter = NoteLeafsAdapter(view_spacing=self.views_spacing)
        self.fbind('views_spacing', view_adapter.setter('view_spacing'))
        rv = self.ids.rv
        rv.view_adapter = view_adapter
        rv.layout_manager.fbind('selected_nodes', self.on_selected_indices)

    def refresh_views(self, *args):
        self.ids.rv.refresh_from_data()

    def _update_rv_data(self, leafs):
        rv = self.ids.rv
        rv.layout_manager.clear_selection()
        rv.data = leafs
        rv.scroll_y = 1.0

    def on_leafs(self, view, leafs):
        self._update_rv_data(leafs)

    def on_selected_indices(self, layout_manager, selected_indices):
        if selected_indices:
            note_leaf = self.ids.rv.data[selected_indices[0]]
            self.dispatch(self.EVENT_LEAF_SELECT, note_leaf)

    def on_leaf_select(self, payload):
        if self.callback:
            self.callback(payload)
        else:
            url = 'https://archive.org/details/{}'.format(payload['key'])
            firefox = webbrowser.get('firefox')
            firefox.open(url)