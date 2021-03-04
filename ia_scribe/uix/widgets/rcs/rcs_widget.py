from functools import reduce
from os.path import join, dirname

from fysom import Fysom
from kivy.lang import Builder
from kivy.properties import (
    StringProperty,
    ObjectProperty,
    ListProperty,
    BooleanProperty,
)
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from ia_scribe.ia_services.rcs import RCS
from ia_scribe.uix.actions.error import ShowErrorAction
from ia_scribe.uix.actions.generic import ColoredYesNoActionPopupMixin
from ia_scribe.uix.actions.input import InputActionPopupMixin
from ia_scribe.uix.components.poppers.popups import WidgetPopup
from ia_scribe.uix.components.selectable_recycleview.selectable_recycleview import \
    SelectableResultView, \
    SelectableRecycleView, \
    SelectableResultsContainer
from ia_scribe.utils import get_scanner_property

Builder.load_file(join(dirname(__file__), 'rcs_widget.kv'))

state_machine_config = {'initial': 'center_selected',
             'events': [
                 {'name': 'select_center', 'src': '*', 'dst': 'center_selected'},
                 {'name': 'select_sponsor', 'src': ['*'], 'dst': 'sponsor_selected'},
                 {'name': 'select_contributor', 'src': ['*'], 'dst': 'contributor_selected'},
                 {'name': 'select_collection', 'src': '*', 'dst': 'collection_selected'},
             ]}


class RCSView(SelectableResultView):
    default = BooleanProperty()
    collections = StringProperty()
    sponsor = StringProperty()
    contributor = StringProperty()
    partner = StringProperty()
    name = StringProperty()


    def refresh_view_attrs(self, rv, index, data):
        self.data = data
        self.collections = str(data.get('collections'))
        self.sponsor = data.get('sponsor')
        self.contributor = data.get('contributor')
        self.partner = data.get('partner')
        self.name = data.get('name', '-- No name --')
        self.default = data.get('default', False)


class RCSWidget(BoxLayout):

    def __init__(self, **kwargs):
        self.rcs = RCS()
        self.data = self.rcs.as_list()
        self.rcs.subscribe(self._rcs_event_handler)
        self.widget = None
        super(RCSWidget, self).__init__(**kwargs)
        Clock.schedule_once(self._postponed_init, -1)

    def _postponed_init(self, *args, **kwargs):
        self.ids.rv.bind(on_entry_selected=self.receive_upstream_selection)
        self._update_rv_data()

    def add_new(self):
        self.widget = WidgetPopup(content_class=RCSSelectionWidget,
                                  title='Add new RCS',
                                  size_hint=(None, None),
                                  size=('800dp', '500dp')
                                  )
        self.widget.bind_events({
            'EVENT_CLOSED': self.widget.dismiss,
            'EVENT_RCS_SELECTED': self._new_rcs_handler,
        })
        self.widget.content.set_center(get_scanner_property('scanningcenter'))
        self.widget.open()

    def delete_entry(self, action, popup, *args, **kwargs):
        target = action.extra_args
        self.rcs.delete(target)

    def set_default_entry(self, action, popup, *args, **kwargs):
        target = action.extra_args
        self.rcs.set_default(target)

    def rename_entry(self, action, popup, value, *args):
        target = action.extra_args
        self.rcs.rename(target, value)

    def _new_rcs_handler(self, widget, rcs_data):
        self.rcs.add(rcs_data)
        self.widget.dismiss()

    def update_from_ia(self, *args, **kwargs):
        self.action = ColoredYesNoActionPopupMixin(
            action_function=self.rcs._do_sync,
            title='Update from IA?',
            message='This action will queue a task that will download the most recent RCS list from IA.'
                    'This already happens in the background every so often, but you may want to force it if you just added one.'
                    '\nYou will [b]not[/b] lose any local data.',
        )
        self.action.display()

    def receive_upstream_selection(self, entry, data, action, *args):
        if action == 'delete':
            self.action = ColoredYesNoActionPopupMixin(
                action_function=self.delete_entry,
                extra=data,
                title='Are you sure?',
                message='Do you want to {} {}?'.format(action, data.get('name')),
            )

        elif action == 'set_default':
            self.action = ColoredYesNoActionPopupMixin(
                action_function=self.set_default_entry,
                extra=data,
                title='Set default RCS for scanning?',
                message='Do you want to select {} as your default RCS?'.format( data.get('name')),
            )
        elif action == 'rename':
            self.action = InputActionPopupMixin(title='Rename collection string',
                                                input_value=data.get('name'),
                                                action_function=self.rename_entry,
                                                extra=data,
                                                )
        self.action.display()

    def _rcs_event_handler(self, *args):
        self.data = self.rcs.as_list()
        self._update_rv_data()

    def _update_rv_data(self, *args):
        rv = self.ids.rv
        rv.data = []
        rv.data = self.data[:]
        rv.scroll_y = 1.0


class RCSSelectionWidget(BoxLayout):

    output = StringProperty()
    centers = ListProperty()
    selected_center = StringProperty()
    sponsors = ListProperty()
    selected_sponsor = StringProperty()
    contributors = ListProperty()
    selected_contributor = StringProperty()
    collections = ListProperty()
    selected_collection = StringProperty()
    current_set = ListProperty()
    selection_state = ObjectProperty()
    set_default = BooleanProperty(False)

    EVENT_RCS_SELECTED = 'on_select_rcs'
    EVENT_CLOSED = 'on_close'

    __events__ = (EVENT_RCS_SELECTED, EVENT_CLOSED,)

    def __init__(self, **kwargs):
        self.rcs = RCS()
        self.centers = self.rcs.remote_get_aggregate('center')
        self.selection_state = Fysom(state_machine_config)
        super(RCSSelectionWidget, self).__init__(**kwargs)

    def set_center(self, center):
        self.ids.center_spinner.spinner_text = center
        self.ids.center_spinner.disabled = True

    def filter(self, key, value):
        return [x for x in self.current_set if x.get(key) == value]

    def get_aggregate(self, key, set):
        ret = [content.get(key) for content in set]
        return set(ret)

    def _update_filter_option(self, spinner, selection):
        key = spinner.key
        val = spinner.spinner_text
        action = spinner.action
        if not self.selection_state.can(action):
            print('error!!! cannot do this')
            return
        self.selection_state.trigger(action)
        self.set_attribute(key, val)
        self.cascade_update()

    def set_attribute(self, key, value):
        setattr(self, 'selected_{}'.format(key), value)

    def cascade_update(self):
        if self.selection_state.current == 'center_selected':
            self.current_set = self.rcs.remote_get_all_in_center(self.selected_center)
            self.sponsors = sorted(set([x['sponsor'] for x in self.current_set]))
        elif self.selection_state.current == 'sponsor_selected':
            filtered_down_set = [x for x in self.current_set if x['sponsor'] == self.selected_sponsor]
            self.contributors = sorted(set([x['contributor'] for x in filtered_down_set]))
        elif self.selection_state.current == 'contributor_selected':
            filtered_down_set = [x for x in self.current_set if x['sponsor'] == self.selected_sponsor and
                                 x['contributor'] == self.selected_contributor]
            self.collections = sorted(set([x['collections'] for x in filtered_down_set]))

    def validate_selection(self):
        clauses = {
            'Collection set selected': self.selection_state.current == 'collection_selected'
                                       and self.collections not in [None, ''],
            'Name selected': self.ids.rcs_name.text not in ['', None]
        }
        is_valid = reduce(lambda x, y: x and y, clauses.values())
        error = [k for k, v in clauses.items() if v is False]
        return is_valid, error

    def collect_data(self):
        is_valid, error, = self.validate_selection()
        if not is_valid:
            raise Exception(error)
        ret = next((x for x in self.current_set if x['collections'] == self.selected_collection
                    and x['sponsor'] == self.selected_sponsor
                    and x['contributor'] == self.selected_contributor), None)
        ret['name'] = self.ids.rcs_name.text
        ret['default'] = self.set_default
        return ret

    def do_select_rcs(self):
        try:
            rcs_payload = self.collect_data()
            self.dispatch(self.EVENT_RCS_SELECTED, rcs_payload)
        except Exception as e:
            message = 'The following conditions were not met:'
            for error in e.message:
                message += '\n- {}'.format(error)
            self.action = ShowErrorAction(message=message)
            self.action.display()

    def do_close(self, *args):
        self.dispatch(self.EVENT_CLOSED)

    def on_close(self, *args):
        pass

    def on_select_rcs(self, *args):
        pass