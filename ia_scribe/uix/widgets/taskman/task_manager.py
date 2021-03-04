from copy import deepcopy
from itertools import chain
from os.path import join, dirname

from kivy.clock import Clock
from kivy.compat import text_type
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import (
    StringProperty,
    NumericProperty,
    ObjectProperty,
    OptionProperty
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from sortedcontainers import SortedListWithKey

from ia_scribe.tasks.task_base import (
    CANCELLED_WITH_ERROR,
    PENDING,
    CANCELLED,
    RESUMING,
    CANCELLING,
    PAUSING,
    DONE,
    RUNNING,
    PAUSED,
    ALL_STATES
)
from ia_scribe.tasks.task_scheduler import ALL_LEVELS

Builder.load_file(join(dirname(__file__), 'task_manager.kv'))

DATE_TIME_FORMAT = '%H:%M:%S\n%Y-%m-%d'
TASK_VIEW_HEADER = [
    {'key': 'name', 'text': 'Task Name', 'width': dp(200)},
    {'key': 'state', 'text': 'State'},
    {'key': 'progress', 'text': 'Progress',
     'size_hint': (1.0, 1.0), 'size_hint_min': (dp(200), None)},
    {'key': 'level_name', 'text': 'Level'},
    {'key': 'started_at', 'text': 'Started At', 'width': dp(120)},
    {'key': 'ended_at', 'text': 'Ended At', 'width': dp(120)},
]
WORKER_VIEW_HEADER = [
    {'key': 'worker_name', 'text': 'Worker name', 'width': dp(200)},
    {'key': 'name', 'text': 'Task Name', 'width': dp(200)},
    {'key': 'level_name', 'text': 'Level'},
    {'key': 'running_since', 'text': 'Running Since', 'width': dp(140)},
    {'key': 'progress', 'text': 'Progress',
     'size_hint': (1.0, 1.0), 'size_hint_min': (dp(200), None)}
]
item = None
for item in chain(TASK_VIEW_HEADER, WORKER_VIEW_HEADER):
    item['sort_order'] = 'asc'
    item['state'] = 'normal'
del item


class TaskView(RecycleDataViewBehavior, BoxLayout):

    index = NumericProperty(-1)
    name = StringProperty('-')
    state = StringProperty('-')
    message = StringProperty('-')
    progress = NumericProperty(0.0)
    level = StringProperty('-')
    started_at = StringProperty()
    ended_at = StringProperty()

    __events__ = ('on_option_select',)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        self.level = data.get('level_name', None) or u''
        self.refresh_from_task(data['task'])

    def refresh_from_task(self, task):
        self.name = task.name
        self.progress = task.last_report.get('progress', None) or 0.0
        self.started_at = self._format_timestamp(task.started_at)
        self.ended_at = self._format_timestamp(task.ended_at)
        self._update_state(task)
        self._update_message(task)
        self._update_buttons(task)

    def _update_state(self, task):
        if task.state == CANCELLED_WITH_ERROR:
            self.state = 'error'
        else:
            self.state = task.state

    def _update_message(self, task):
        if task.periodic \
                and task.state in {PENDING, RESUMING, CANCELLING, PAUSING}\
                and not task.last_report.get('progress', None)\
                and not task.first_start:
            self.message = u'Waiting for %s seconds' % task.interval
        else:
            self.message = task.last_report.get('message', None) or u''

    def _update_buttons(self, task):
        state = task.state
        disabled = state in {CANCELLING, CANCELLED_WITH_ERROR, DONE}
        self.ids.pause_resume_button.disabled = disabled
        self.ids.cancel_button.disabled = disabled
        self.ids.pause_resume_button.text = 'Pause'
        self.ids.cancel_button.text = 'Cancel'
        if task.can_retry():
            self.ids.pause_resume_button.text = 'Pause'
            self.ids.pause_resume_button.disabled = True
            self.ids.cancel_button.text = 'Retry'
            self.ids.cancel_button.disabled = False
        elif state in {PAUSED, PAUSING}:
            self.ids.pause_resume_button.text = 'Resume'

    def _on_pause_resume_button_release(self, *args):
        self.dispatch('on_option_select', 'pause_resume')

    def _on_cancel_button_release(self, *args):
        self.dispatch('on_option_select', 'cancel_retry')

    def _format_timestamp(self, timestamp):
        return timestamp.strftime(DATE_TIME_FORMAT) if timestamp else u''

    def on_option_select(self, option):
        pass


class WorkerView(RecycleDataViewBehavior, BoxLayout):

    index = NumericProperty(-1)
    worker_name = StringProperty('-')
    running_since = StringProperty('-')
    name = StringProperty('-')
    level = StringProperty('-')
    message = StringProperty('-')
    progress = NumericProperty(0.0)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        self.worker_name = data.get('worker_name', None) or u''
        self.level = data.get('level_name', None) or u''
        self.running_since = \
            self._format_timestamp(data.get('running_since', None))
        task = data.get('task', None)
        self.name = task.name if task else u''
        self.progress = \
            task.last_report.get('progress', None) or 0.0 if task else 0.0
        self.message = \
            task.last_report.get('message', None) or u'' if task else u''

    def _format_timestamp(self, timestamp):
        return timestamp.strftime(DATE_TIME_FORMAT) if timestamp else u''


class TaskViewLayout(RecycleGridLayout):

    __events__ = ('on_task_option_select',)

    def add_widget(self, widget, index=0):
        if isinstance(widget, TaskView):
            widget.fbind('on_option_select', self._on_option_select)
        super(TaskViewLayout, self).add_widget(widget, index)

    def remove_widget(self, widget):
        if isinstance(widget, TaskView):
            widget.funbind('on_option_select', self._on_option_select)
        super(TaskViewLayout, self).remove_widget(widget)

    def _on_option_select(self, task_view, option):
        self.dispatch('on_task_option_select', task_view, option)

    def on_task_option_select(self, task_view, option):
        pass


class TaskManagerFilterHeader(GridLayout):

    filter_option = ObjectProperty(
        {'type': 'all', 'state': 'all', 'level_name': 'all', 'periodic': 'all'}
    )
    type_values = ObjectProperty(['all'])
    state_values = ObjectProperty(['all'] + list(sorted(ALL_STATES)))
    level_values = ObjectProperty(['all'] + list(sorted(ALL_LEVELS)))
    periodic_values = ObjectProperty(['all', 'yes', 'no'])

    view_option = OptionProperty('tasks_view',
                                 options=['tasks_view', 'workers_view'])

    def _update_filter_option(self, *args):
        ids = self.ids
        self.filter_option = {
            'type': ids.type_spinner.spinner_text,
            'state': ids.state_spinner.spinner_text,
            'level_name': ids.level_spinner.spinner_text,
            'periodic': ids.periodic_spinner.spinner_text
        }


class TaskManager(BoxLayout):

    def __init__(self, **kwargs):
        self._task_scheduler = None
        self._all_task_items = SortedListWithKey(key=hash)
        self._all_worker_items = \
            SortedListWithKey(key=lambda x: x['worker_name'])
        self._trigger_filtering = Clock.create_trigger(self._do_filtering, -1)
        self._old_view_option = view_option = 'tasks_view'
        self._sort_key_store = {
            'tasks_view': {'key': 'name', 'sort_order': 'asc'},
            'workers_view': {'key': 'worker_name', 'sort_order': 'asc'}
        }
        self._sort_key = self._sort_key_store[view_option]['key']
        self._sort_order = self._sort_key_store[view_option]['sort_order']
        super(TaskManager, self).__init__(**kwargs)
        Clock.schedule_once(self._postponed_init, -1)

    def _postponed_init(self, *args):
        ids = self.ids
        ids.filter_header.fbind('filter_option', self._do_filtering)
        ids.filter_header.fbind('view_option', self._on_view_option)
        ids.rv.layout_manager.fbind('on_task_option_select',
                                    self._on_task_option_select)
        ids.header.fbind('on_selection', self._on_sort_option_select)
        self._on_view_option(ids.filter_header, ids.filter_header.view_option)

    def attach_scheduler(self, scheduler):
        task_items = scheduler.get_all_tasks()
        for task_item in task_items:
            self._fbind_task(task_item['task'])
        scheduler.fbind('on_task_item_add', self._on_task_item_add)
        scheduler.fbind('on_task_item_remove', self._on_task_item_remove)
        scheduler.fbind('on_task_item_change', self._on_task_item_change)
        scheduler.fbind('on_worker_item_change', self._on_worker_item_change)
        self._task_scheduler = scheduler
        self._all_task_items.update(task_items)
        self._all_worker_items.update(scheduler.get_all_workers())
        self._update_filter_header_options()
        self._trigger_filtering()

    def detach_scheduler(self):
        scheduler = self._task_scheduler
        self._task_scheduler = None
        scheduler.funbind('on_task_item_add', self._on_task_item_add)
        scheduler.funbind('on_task_item_remove', self._on_task_item_remove)
        scheduler.funbind('on_task_item_change', self._on_task_item_change)
        scheduler.funbind('on_worker_item_change', self._on_worker_item_change)
        for task_item in self._all_task_items:
            self._funbind_task(task_item['task'])
        self.clear_tasks()

    def clear_tasks(self):
        self._all_task_items.clear()
        self._all_worker_items.clear()
        self._update_filter_header_options()
        self._trigger_filtering()

    def _do_filtering(self, *args):
        items = self._get_items_for_current_view()
        items = self._filter_and_sort_items(items)
        self._update_rv(items)

    def _do_sorting(self, *args):
        items = self._sort_items()
        self._update_rv(items, scroll_to_top=True)

    def _sort_items(self):
        return sorted(
            self.ids.rv.data,
            key=self._key_function,
            reverse=self._sort_order == 'desc'
        )

    def _filter_and_sort_items(self, items):
        order = self._sort_order
        option = self.ids.filter_header.filter_option
        matched = SortedListWithKey(key=self._key_function)
        check = 0
        for item in items:
            task = item['task']
            check = 0
            if option['type'] == 'all' \
                    or task and type(task).__name__ == option['type']:
                check += 1
            if option['state'] == 'all' \
                    or task and task.state == option['state']:
                check += 1
            if option['level_name'] == 'all' \
                    or item['level_name'] == option['level_name']:
                check += 1
            if option['periodic'] == 'all' or task and \
                    (option['periodic'] == 'yes' and task.periodic
                     or option['periodic'] == 'no' and not task.periodic):
                check += 1
            if check == len(option):
                matched.add(item)
        return reversed(matched) if order == 'desc' else matched

    def _key_function(self, item):
        key = self._sort_key
        if key == 'progress':
            if item.get('task', None):
                return item['task'].last_report.get('progress', 0.0)
            return 0.0
        elif key in set(item.keys()):
            return text_type(item[key])
        elif item.get('task', None):
            return text_type(getattr(item['task'], key))
        return u''

    def _update_rv(self, items, scroll_to_top=False):
        rv = self.ids.rv
        rv.data = items
        if scroll_to_top:
            rv.scroll_y = 1.0

    def _update_filter_header_options(self, *args):
        task_items = self._all_task_items
        all_types = set([type(item['task']).__name__ for item in task_items])
        self.ids.filter_header.type_values = ['all'] + list(all_types)

    def _get_items_for_current_view(self):
        view_option = self.ids.filter_header.view_option
        if view_option == 'tasks_view':
            return self._all_task_items
        elif view_option == 'workers_view':
            return self._all_worker_items
        return []

    def _on_sort_option_select(self, header, option):
        self._sort_key = option[0]['key']
        self._sort_order = option[0]['sort_order']
        self._do_sorting()

    def _on_view_option(self, filter_header, option):
        changed = False
        old_option = self._old_view_option
        store = self._sort_key_store
        if option == 'tasks_view':
            self.ids.rv.viewclass = 'TaskView'
            self.ids.header.data = deepcopy(TASK_VIEW_HEADER)
            changed = True
        elif option == 'workers_view':
            self.ids.rv.viewclass = 'WorkerView'
            self.ids.header.data = deepcopy(WORKER_VIEW_HEADER)
            changed = True
        if changed:
            store[old_option]['key'] = self._sort_key
            store[old_option]['sort_order'] = self._sort_order
            self._sort_key = store[option]['key']
            self._sort_order = store[option]['sort_order']
            self._old_view_option = option
            for item in self.ids.header.data:
                if item['key'] == self._sort_key:
                    item['state'] = 'down'
                    item['sort_order'] = self._sort_order
                    break
            self._do_filtering()

    def _on_task_item_add(self, scheduler, task_item):
        self._fbind_task(task_item['task'])
        self._all_task_items.add(task_item)
        self._update_filter_header_options()
        self._trigger_filtering()

    def _on_task_item_remove(self, scheduler, task_item):
        self._funbind_task(task_item['task'])
        self._all_task_items.remove(task_item)
        self._update_filter_header_options()
        self._trigger_filtering()

    def _on_task_item_change(self, scheduler, task_item):
        index = self._all_task_items.index(task_item)
        _task_item = self._all_task_items[index]
        _task_item.update(task_item)
        self._trigger_filtering()

    def _on_worker_item_change(self, scheduler, worker_item):
        index = self._all_worker_items.bisect(worker_item) - 1
        _worker_item = self._all_worker_items[index]
        _worker_item.update(worker_item)
        self._trigger_filtering()

    def _on_task_option_select(self, layout_manager, task_view, option):
        index = task_view.index
        task = self.ids.rv.data[index]['task']
        if option == 'pause_resume':
            if task.state == PAUSED and task.resume():
                task_view.refresh_from_task(task)
            elif task.state in {PENDING, RUNNING, RESUMING} and task.pause():
                task_view.refresh_from_task(task)
        elif option == 'cancel_retry':
            if task.can_retry() and task.retry():
                task_view.refresh_from_task(task)
            elif task.cancel():
                task_view.refresh_from_task(task)

    def _fbind_task(self, task):
        task.fbind('on_state', self._trigger_filtering)
        task.fbind('on_progress', self._trigger_filtering)

    def _funbind_task(self, task):
        task.funbind('on_state', self._trigger_filtering)
        task.funbind('on_progress', self._trigger_filtering)

    def _on_option_select(self, option):
        for task_item in self.ids.rv.data:
            getattr(task_item['task'], option)()
