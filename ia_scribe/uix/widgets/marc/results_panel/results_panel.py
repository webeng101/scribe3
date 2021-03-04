from os.path import join, dirname

from kivy.lang import Builder
from kivy.properties import (ListProperty,
                            StringProperty,
                            ObjectProperty,
                             DictProperty)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.recycleview.views import RecycleDataViewBehavior

from ia_scribe.uix.components.poppers.popups import InfoPopup, Popup
from ia_scribe.uix.widgets.marc.results_panel.details_panel import MARCDetails

Builder.load_file(join(dirname(__file__), 'results_panel.kv'))


def show_popup( title, label):
    popup = InfoPopup(
        title=title,
        message=(label),
        auto_dismiss=False
    )
    popup.bind(on_submit=popup.dismiss)
    popup.open()


class MARCResultView(RecycleDataViewBehavior, BoxLayout):

    EVENT_SELECTED = 'on_selection'
    __events__ = (EVENT_SELECTED,)

    title = StringProperty()
    creator = StringProperty()
    date = StringProperty()
    publisher = StringProperty()
    isbn = StringProperty()
    language = StringProperty()
    subject = StringProperty()
    data = DictProperty()

    def refresh_view_attrs(self, rv, index, data):
        self.data = data
        for entry in ['title', 'creator', 'date',
                      'publisher', 'language', 'subject']:
            val = data.get(entry, '')
            value = u'{}'.format(val)
            if not value:
                value = ''
            setattr(self, entry, value)
        isbn = data.get('isbn')
        if isbn:
            self.isbn = ' | '.join(isbn.values())

        subject = data.get('subject')
        if type(subject) in [dict, list]:
            self.subject = ' | '.join(subject.values())
        else:
            self.subject = subject if subject is not None else ''

    def select_result(self, *args):
        self.dispatch(self.EVENT_SELECTED)

    def show_details(self):
        content = MARCDetails()
        content.data = self.data
        popup = Popup(
            title='MARC Details',
            content=content,
            auto_dismiss=True,
            size_hint=(.80, .80)
        )
        content.fbind(content.EVENT_BUTTON_CLOSED_PRESSED,popup.dismiss)
        popup.open()

    def on_selection(self, *args):
        pass


class MARCResultsContainer(RecycleGridLayout):
    def __init__(self, **kwargs):
        super(MARCResultsContainer, self).__init__(**kwargs)

    __events__ = ('on_view_added', 'on_view_removed')

    def add_widget(self, widget, index=0):
        super(MARCResultsContainer, self).add_widget(widget, index)
        self.dispatch('on_view_added', widget)

    def remove_widget(self, widget):
        super(MARCResultsContainer, self).remove_widget(widget)
        self.dispatch('on_view_removed', widget)

    def on_view_added(self, view):
        pass

    def on_view_removed(self, view):
        pass

class MARCRecycleView(RecycleView):
    EVENT_ENTRY_SELECTED = 'on_entry_selected'

    __events__ = (EVENT_ENTRY_SELECTED, )

    def __init__(self, **kwargs):
        super(MARCRecycleView, self).__init__(**kwargs)

    def on_layout_manager(self, view, layout_manager):
        if layout_manager:
            layout_manager.bind(on_view_added=self._on_view_added,
                                on_view_removed=self._on_view_removed)

    def _on_view_added(self, layout_manager, view):
        if isinstance(view, MARCResultView):
            view.fbind('on_selection', self._on_view_select)

    def _on_view_removed(self, layout_manager, view):
        if isinstance(view, MARCResultView):
            view.funbind('on_selection', self._on_view_select)

    def _on_view_select(self, widget):
        self.dispatch(self.EVENT_ENTRY_SELECTED, widget.data)

    def on_entry_selected(self, *args):
        pass

class MARCResultsPanel(BoxLayout):
    raw_results = DictProperty()
    results = ListProperty()
    unfiltered_results = ListProperty()
    search_backend = ObjectProperty()
    change_title_callback = ObjectProperty()
    filter_text = StringProperty()

    EVENT_GOT_SEARCH_RESULTS = 'on_got_search_results'
    EVENT_GO_PREVIOUS = 'on_go_previous'
    EVENT_GO_NEXT = 'on_go_next'
    EVENT_RESULT_SELECT = 'on_result_select'
    EVENT_LOAD_MORE_START = 'on_load_more_started'

    __events__ = (EVENT_RESULT_SELECT, EVENT_GO_PREVIOUS, EVENT_GO_NEXT,
                  EVENT_LOAD_MORE_START, EVENT_GOT_SEARCH_RESULTS)

    def __init__(self, *args, **kwargs):
        super(MARCResultsPanel, self).__init__(**kwargs)
        self.results = []

    def postponed_init(self):
        self.search_backend.fbind(self.search_backend.EVENT_SEARCH_RESULTS,
                                  self.on_search_results)
        self.ids.rv.bind(on_entry_selected=self.receive_upstream_selection)

    def on_search_results(self, *args):
        if self.search_backend.results:
            self.raw_results = self.search_backend.results
            self.results = self.unfiltered_results = [value['dc_meta']['metadata']
                        for entry, value in self.raw_results['recs'].items()]

            # this is what causes the screen to change to the results page
            self.dispatch(self.EVENT_GOT_SEARCH_RESULTS)

    def on_got_search_results(self):
        self.change_title_callback('{total} results for query [b]{query}[/b] in {catalog}'
                                   ' [{page}/{total}]'.format(
                                            total = self.search_backend.results['query']['hits'],
                                            query = self.search_backend.query,
                                            catalog = self.search_backend.results['query']['catalog'],
                                            page=self.search_backend.results['query']['offset']))

    def on_results(self, *args):
        self._update_rv_data()

    def _update_rv_data(self, *args):
        rv = self.ids.rv
        rv.data = self.results[:]
        rv.scroll_y = 1.0

    def receive_upstream_selection(self, widget, data):
        query = self.raw_results['query']
        full_record = [y for x, y in self.raw_results.recs.items() if y['dc_meta']['metadata'] == dict(data)][0]
        self.dispatch(self.EVENT_RESULT_SELECT, query, full_record)

    def on_result_select(self, *args):
        pass

    def on_go_previous(self, *args):
        if self.search_backend.go_previous():
            self.dispatch(self.EVENT_LOAD_MORE_START)

    def on_go_next(self, *args):
        if self.search_backend.go_next():
            self.dispatch(self.EVENT_LOAD_MORE_START)

    def on_load_more_started(self, *args):
        pass

    def on_filter_text(self, filter_input, text):
        self.results = self.filter(text)

    def filter(self, text):
        if text == '':
            return self.unfiltered_results
        else:
            return [x for x in self.unfiltered_results
                    if text in x['title']
                    or text in ['creator']]

