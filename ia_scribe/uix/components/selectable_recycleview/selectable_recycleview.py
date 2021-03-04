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

Builder.load_file(join(dirname(__file__), 'selectable_recycleview.kv'))

class SelectableResultView(RecycleDataViewBehavior, BoxLayout):

    EVENT_SELECTED = 'on_selection'
    __events__ = (EVENT_SELECTED,)

    data = DictProperty()

    def refresh_view_attrs(self, rv, index, data):
        self.data = data

    def select_result(self, action=None, *args):
        self.dispatch(self.EVENT_SELECTED, action, *args)

    def on_selection(self, *args):
        pass

class ConcreteSelectableResultView(SelectableResultView):
    pass

class SelectableResultsContainer(RecycleGridLayout):
    def __init__(self, **kwargs):
        super(SelectableResultsContainer, self).__init__(**kwargs)

    __events__ = ('on_view_added', 'on_view_removed')

    def add_widget(self, widget, index=0):
        super(SelectableResultsContainer, self).add_widget(widget, index)
        self.dispatch('on_view_added', widget)

    def remove_widget(self, widget):
        super(SelectableResultsContainer, self).remove_widget(widget)
        self.dispatch('on_view_removed', widget)

    def on_view_added(self, view):
        pass

    def on_view_removed(self, view):
        pass

class SelectableRecycleView(RecycleView):
    EVENT_ENTRY_SELECTED = 'on_entry_selected'

    __events__ = (EVENT_ENTRY_SELECTED, )

    def __init__(self, **kwargs):
        super(SelectableRecycleView, self).__init__(**kwargs)

    def on_layout_manager(self, view, layout_manager):
        if layout_manager:
            layout_manager.bind(on_view_added=self._on_view_added,
                                on_view_removed=self._on_view_removed)

    def _on_view_added(self, layout_manager, view):
        if isinstance(view, SelectableResultView):
            view.fbind('on_selection', self._on_view_select)

    def _on_view_removed(self, layout_manager, view):
        if isinstance(view, SelectableResultView):
            view.funbind('on_selection', self._on_view_select)

    def _on_view_select(self, widget, action, *args):
        self.dispatch(self.EVENT_ENTRY_SELECTED, widget.data, action, *args)

    def on_entry_selected(self, *args):
        pass