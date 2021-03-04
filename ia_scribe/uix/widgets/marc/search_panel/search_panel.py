from collections import Counter
from functools import  partial
from os.path import join, dirname

from kivy.compat import text_type
from kivy.lang import Builder
from kivy.properties import (StringProperty,
                             BooleanProperty,
                             NumericProperty,
                             ListProperty,
                             ObjectProperty)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior

from ia_scribe.uix.behaviors.form import FormBehavior
from ia_scribe.uix.components.poppers.popups import InfoPopup

Builder.load_file(join(dirname(__file__), 'search_panel.kv'))

MD_BASIC_KEYS = ['title', 'author', 'date']


class TextBoxItem(RecycleDataViewBehavior, BoxLayout):

    index = NumericProperty()
    key = StringProperty()
    text = StringProperty()
    readonly = BooleanProperty(False)

    message = StringProperty()
    focus = BooleanProperty(False)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        self.focus = False
        self.key = self._format_key(data['key'])
        self.readonly = readonly = data.get('readonly', False)
        self.text = text_type(data['value'])
        self.disabled = rv.layout_manager.disabled
        self.validate(data)

    def validate(self, data):
        self.message = ''
        if not data.get('valid', True):
            self.message = data.get('message', '')

    def _format_key(self, key):
        return u'{}:'.format(key.capitalize())


class MARCSearchLayout(RecycleGridLayout):

    __events__ = ('on_view_added', 'on_view_removed')

    def add_widget(self, widget, index=0):
        super(MARCSearchLayout, self).add_widget(widget, index)
        self.dispatch('on_view_added', widget)

    def remove_widget(self, widget):
        super(MARCSearchLayout, self).remove_widget(widget)
        self.dispatch('on_view_removed', widget)

    def on_view_added(self, view):
        pass

    def on_view_removed(self, view):
        pass

class MARCSearchView(FormBehavior, RecycleView):

    use_basic_view = BooleanProperty(True)

    def __init__(self, **kwargs):
        self.all_data = []
        self.all_data_keys = Counter()
        self.fbind('use_basic_view', self._do_filtering)
        super(MARCSearchView, self).__init__(**kwargs)

    def set_data(self, data):
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
        for item in self.data:
            if 'view_class' not in item:
                # It's a default view_class == TextBoxItem
                metadata.append(item)
        return metadata

    def validate(self, *args):
        view_class = self.layout_manager.key_viewclass
        for item in self.all_data:
            if view_class not in item:
                self.validate_item(item)
        self.refresh_from_data()

    def validate_item(self, item):
        key, value = item['key'], item['value']
        item['valid'] = True

    def on_layout_manager(self, view, layout_manager):
        if layout_manager:
            layout_manager.key_viewclass = 'view_class'
            layout_manager.bind(on_view_added=self._on_view_added,
                                on_view_removed=self._on_view_removed)

    def _on_view_added(self, layout_manager, view):
        if isinstance(view, TextBoxItem):
            view.fbind('text', self._on_view_text_input)

    def _on_view_removed(self, layout_manager, view):
        if isinstance(view, TextBoxItem):
            view.funbind('text', self._on_view_text_input)

    def _do_filtering(self, *args):
        if self.use_basic_view:
            self.data = filter(
                lambda x: 'key' not in x or x['key'] in MD_BASIC_KEYS,
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

class MARCSearchPanel(BoxLayout):
    search_form = ObjectProperty()
    catalogs = ListProperty()
    current_catalog = StringProperty()
    catalogs_backend = ObjectProperty()
    filter_text = StringProperty()
    search_backend = ObjectProperty()
    change_title_callback = ObjectProperty()

    EVENT_SEARCH_STARTED = 'on_search_started'
    EVENT_ON_SEARCH_RESULTS = 'on_search_results'
    EVENT_ON_SEARCH_FAILURE = 'on_search_failure'

    __events__ = (EVENT_SEARCH_STARTED, EVENT_ON_SEARCH_RESULTS, EVENT_ON_SEARCH_FAILURE)

    def __init__(self, *args, **kwargs):
        super(MARCSearchPanel, self).__init__(**kwargs)
        self.search_form = MARCSearchView()

    def postponed_init(self):
        self.catalogs_backend.fbind(self.catalogs_backend.EVENT_CATALOGS_LOADED,
                                    self.update_catalogs)
        self.catalogs_backend.fbind(self.catalogs_backend.EVENT_CATALOGS_CHANGED,
                                    self.update_catalogs)
        self.catalogs_backend.init()


        self.fbind(self.EVENT_SEARCH_STARTED, self.search_backend.search)
        self.search_backend.fbind(self.search_backend.EVENT_SEARCH_FAILURE,
                                  partial(self.dispatch, self.EVENT_ON_SEARCH_FAILURE))
        self.search_backend.init()

    def on_leave(self, *args):
        self.catalogs_backend.reset()

    def on_search_form(self, source, target):
        self.ids.content.clear_widgets()
        self.ids.content.add_widget(target)

    def update_catalogs(self, backend):
        self.catalogs = backend.get_catalogs_list()

    def toggle_expand(self):
        self.search_form.use_basic_view = not self.search_form.use_basic_view
        return 'Show Basic' if not self.search_form.use_basic_view else 'Show All'

    def get_filled_data(self, data):
        for item in data:
            if item.get('value') != u'':
                yield item

    def is_data_enough_for_search(self, data):
        ret = False
        for item in self.get_filled_data(data):
            ret = True
        return ret

    def do_search(self):
        data = list(self.get_filled_data(self.search_form.collect_data()))
        if not self.is_data_enough_for_search(data):
            self.show_popup('Not enough data', 'Not a lot to work with, buddy...')
            return
        self.dispatch(self.EVENT_SEARCH_STARTED,
                      form_data=data, catalog=self.current_catalog)

    def show_popup(self, title, label):
        popup = InfoPopup(
            title=title,
            message=label,
            auto_dismiss=False
        )
        popup.bind(on_submit=popup.dismiss)
        popup.open()

    def on_search_started(self, *args, **kwargs):
        pass

    def on_search_results(self, *args):
        pass

    def on_search_failure(self, *args):
        self.show_popup('Error while searching', str(self.search_backend.error))

    def set_catalog(self, spinner, text):
        keys_list = self.catalogs_backend.get_fields(text)
        self.set_md_fields(keys_list)
        self.current_catalog = text


    def set_md_fields(self, keys_list):
        md = [{'key': k, 'value': u''} for k in keys_list]
        self.search_form.set_data(md)

    def on_filter_text(self, filter_input, text):
        self.catalogs = self.catalogs_backend.filter(text)

