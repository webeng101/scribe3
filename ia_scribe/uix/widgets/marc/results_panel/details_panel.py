from os.path import join, dirname

from kivy.uix.label import Label
from kivy.lang import Builder
from kivy.properties import (ListProperty,
                            StringProperty,
                            ObjectProperty,
                             DictProperty)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.recycleview.views import RecycleDataViewBehavior

Builder.load_file(join(dirname(__file__), 'details_panel.kv'))


class MARCDetails(BoxLayout):

    data = DictProperty()
    EVENT_BUTTON_CLOSED_PRESSED = 'on_button_closed_pressed'

    __events__ = (EVENT_BUTTON_CLOSED_PRESSED,)

    def __init__(self, *args, **kwargs):
        super(MARCDetails, self).__init__(**kwargs)

    def on_button_closed_pressed(self):
        pass

    def on_data(self, *args):
        self._update_rv_data()

    def _update_rv_data(self, *args):
        rv = self.ids.rv
        rv.data = [{k: v} for k, v in self.data.items() if v not in ['', None]]
        rv.scroll_y = 1.0


class MARCDetailsView(RecycleDataViewBehavior, BoxLayout):

    key = StringProperty()
    value = StringProperty()

    def refresh_view_attrs(self, rv, index, data):
        self.key = self.format_value(next(iter(data.keys())))
        self.value = self.format_value(next(iter(data.values())))

    @staticmethod
    def format_value(v):
        if not hasattr(v, 'encode'):
            if type(v) is dict:
                v = ' '.join([value for key, value in v.items()])
            else:
                v = str(v)
        ret = v if v is not None else 'unknown'
        return ret


class OverflowLabel(Label):
    pass

