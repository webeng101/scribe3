from kivy.properties import AliasProperty
from kivy.uix.gridlayout import GridLayout
from kivy.uix.recycleview import RecycleViewBehavior
from kivy.uix.recycleview.datamodel import RecycleDataModel
from kivy.uix.recycleview.layout import RecycleLayoutManagerBehavior
from kivy.uix.recycleview.views import RecycleDataAdapter


class RecycleButtons(RecycleViewBehavior, GridLayout):

    def _get_data(self):
        d = self.data_model
        return d and d.data

    def _set_data(self, value):
        d = self.data_model
        if d is not None:
            d.data = value

    data = AliasProperty(_get_data, _set_data, bind=['data_model'])

    def _get_viewclass(self):
        a = self.layout_manager
        return a and a.viewclass

    def _set_viewclass(self, value):
        a = self.layout_manager
        if a:
            a.viewclass = value

    viewclass = AliasProperty(_get_viewclass, _set_viewclass,
                              bind=['layout_manager'])

    __events__ = ('on_selection',)

    def __init__(self, **kwargs):
        if self.data_model is None:
            kwargs.setdefault('data_model', RecycleDataModel())
        if self.view_adapter is None:
            kwargs.setdefault('view_adapter', RecycleDataAdapter())
        kwargs.setdefault('cols', 1)
        super(RecycleButtons, self).__init__(**kwargs)
        fbind = self.fbind
        fbind('size', self.refresh_from_viewport)
        fbind('pos', self.refresh_from_viewport)
        self.refresh_from_data()

    def add_widget(self, widget, *args):
        super(RecycleButtons, self).add_widget(widget, *args)
        if (isinstance(widget, RecycleLayoutManagerBehavior) and
                not self.layout_manager):
            self.layout_manager = widget
            widget.fbind('selected_nodes', self._on_selected_nodes)

    def remove_widget(self, widget, *args):
        super(RecycleButtons, self).remove_widget(widget, *args)
        if self.layout_manager == widget:
            widget.funbind('selected_nodes', self._on_selected_nodes)
            self.layout_manager = None

    def get_viewport(self):
        lm = self.layout_manager
        return lm.x, lm.y, lm.width, lm.height

    def _on_selected_nodes(self, layout_manager, selected_nodes):
        if selected_nodes:
            selection = [self.data[node] for node in selected_nodes]
            layout_manager.clear_selection()
            self.dispatch('on_selection', selection)

    def on_selection(self, selection):
        pass


