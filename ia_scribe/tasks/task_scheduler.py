from datetime import datetime
from functools import partial
from itertools import chain
from threading import Thread, Condition
from time import time

from kivy.clock import Clock
from kivy.event import EventDispatcher

from ia_scribe.tasks.task_base import (
    PENDING,
    RUNNING,
    PAUSING,
    PAUSED,
    RESUMING,
    CANCELLING,
    CANCELLED,
    CANCELLED_WITH_ERROR,
    DONE
)

LEVEL_DONE_TASKS_LIMIT = 100
_WORKER_MAINTHREAD_NAME = 'MainThread'
LEVEL_MAINTHREAD = 'mainthread'
LEVEL_HIGH = 'high'
LEVEL_LOW = 'low'
LEVEL_MEDIUM = 'medium'
ALL_LEVELS = {LEVEL_MAINTHREAD, LEVEL_HIGH, LEVEL_MEDIUM, LEVEL_LOW}


class TaskItem(dict):

    def __eq__(self, other):
        return self['task'] is other['task']

    def __hash__(self):
        return hash(self['task'])

    def update(self, E=None, **F):
        if E and isinstance(E, TaskItem):
            for key in E:
                if key != 'task':
                    self[key] = E[key]
        for key in F:
            if key != 'task':
                self[key] = F[key]


class TaskScheduler(EventDispatcher):

    __events__ = ('on_task_item_add', 'on_task_item_remove',
                  'on_task_item_change', 'on_worker_item_change')

    def __init__(self, **kwargs):
        super(TaskScheduler, self).__init__(**kwargs)
        self._clock_event = None
        self._main_thread_task = None
        self._all_workers_stop_running = False
        self._running = False
        self._services = {}
        self._levels = {
            LEVEL_MAINTHREAD: self._create_level(worker_count=1,
                                                 timeout=1/30.0),
            LEVEL_HIGH: self._create_level(worker_count=4),
            LEVEL_MEDIUM: self._create_level(worker_count=8),
            LEVEL_LOW: self._create_level(worker_count=4),
        }

    def start(self):
        self._all_workers_stop_running = False
        create_worker_data = self._create_worker_data
        for level_name in self._iter_level_names():
            level = self._levels[level_name]
            for index in range(level['worker_count']):
                name = '%sThread%s' % (level_name.capitalize(), index + 1)
                thread = self._create_thread(level, level_name, name)
                level['worker_task'][name] = create_worker_data()
                level['workers'].append(thread)
                thread.start()
        level = self._levels[LEVEL_MAINTHREAD]
        level['worker_task'][_WORKER_MAINTHREAD_NAME] = create_worker_data()
        self._clock_event = \
            Clock.schedule_interval(self._main_thread_run, level['timeout'])
        self._running = True

    def stop(self):
        self.cancel_all()
        self._all_workers_stop_running = True
        for level_name in self._iter_level_names():
            level = self._levels[level_name]
            for worker in level['workers']:
                worker.join()
            with level['condition']:
                del level['workers'][:]
                del level['waiting'][:]
                del level['running'][:]
                del level['done'][:]
                level['worker_task'].clear()
        if self._clock_event:
            self._clock_event.cancel()
            self._clock_event = None
        self._main_thread_stop()
        self._running = False

    def is_running(self):
        return self._running

    def schedule(self, task, level_name=None):
        level_name = level_name or self._detect_level(task)
        if level_name == LEVEL_MAINTHREAD:
            level = self._levels[level_name]
            level['waiting'].append(task)
        else:
            level = self._levels[level_name]
            condition = level['condition']
            with condition:
                task.set_state_condition(condition)
                level['waiting'].append(task)
                condition.notify()
        self.dispatch('on_task_item_add',
                      self._create_task_item(task, level_name))

    def get_all_tasks(self):
        out = []
        for level_name in self._iter_level_names():
            level = self._levels[level_name]
            with level['condition']:
                for task in chain(level['running'],
                                  level['waiting'],
                                  level['done']):
                    out.append(self._create_task_item(task, level_name))
        level = self._levels[LEVEL_MAINTHREAD]
        for task in chain(level['running'], level['waiting'], level['done']):
            out.append(self._create_task_item(task, LEVEL_MAINTHREAD))
        return out

    def get_all_workers(self):
        out = []
        create_worker_item = self._create_worker_item
        for level_name in self._iter_level_names():
            level = self._levels[level_name]
            with level['condition']:
                for worker in level['workers']:
                    worker_data = level['worker_task'][worker.name]
                    item = create_worker_item(worker.name, level_name,
                                              worker_data['task'],
                                              worker_data['running_since'])
                    out.append(item)
        level = self._levels[LEVEL_MAINTHREAD]
        if level['workers']:
            worker_data = level['worker_task'][_WORKER_MAINTHREAD_NAME]
            item = create_worker_item(_WORKER_MAINTHREAD_NAME,
                                      LEVEL_MAINTHREAD,
                                      worker_data['task'],
                                      worker_data['running_since'])
            out.append(item)
        return out

    def pause_all(self):
        self._call_method_for_all_tasks('pause')

    def resume_all(self):
        self._call_method_for_all_tasks('resume')

    def cancel_all(self):
        self._call_method_for_all_tasks('cancel')

    def register_service(self, service, service_name, level_name=LEVEL_MEDIUM):
        service.task_scheduler = self
        self._services[service_name] = service
        self.schedule(service, level_name)

    def unregister_service(self, service_name):
        service = self._services.pop(service_name)
        service.cancel()
        service.task_scheduler = None

    def get_service(self, service_name):
        return self._services[service_name]

    def mainthread_dispatch(self, event_name, *args):
        Clock.schedule_once(partial(self.dispatch_callback, event_name, args))

    def dispatch_callback(self, event_name, args, dt):
        self.dispatch(event_name, *args)

    def _iter_level_names(self, skip_mainthread=True):
        for level_name in self._levels:
            if skip_mainthread and level_name == LEVEL_MAINTHREAD:
                continue
            yield level_name

    def _call_method_for_all_tasks(self, method_name):
        for level_name in self._iter_level_names():
            level = self._levels[level_name]
            with level['condition']:
                for task in chain(level['running'], level['waiting']):
                    getattr(task, method_name)()
        if self._main_thread_task:
            getattr(self._main_thread_task, method_name)()
        level = self._levels[LEVEL_MAINTHREAD]
        for task in chain(level['running'], level['waiting']):
            getattr(task, method_name)()

    def _create_task_item(self, task, level_name, worker_name=None,
                          running_since=None):
        return TaskItem({'task': task,
                         'level_name': level_name,
                         'worker_name': worker_name,
                         'running_since': running_since})

    def _create_worker_item(self, worker_name, level_name, task=None,
                            running_since=None):
        return {
            'task': task,
            'worker_name': worker_name,
            'level_name': level_name,
            'running_since': running_since
        }

    def _create_worker_data(self, task=None, running_since=None):
        return {'task': task, 'running_since': running_since}

    def _create_level(self, worker_count=1, timeout=1/10.0):
        return {
            'workers': [],
            'waiting': [],
            'running': [],
            'done': [],
            'condition': Condition(),
            'worker_count': worker_count,
            'worker_task': {},
            'timeout': timeout
        }

    def _detect_level(self, task):
        # Support explicit priority setting in task (only if valid)
        if hasattr(task, '_priority') and task._priority in ALL_LEVELS:
            return task._priority
        if task.periodic and task.run_in_thread:
            return LEVEL_MEDIUM
        elif not task.periodic and task.run_in_thread:
            return LEVEL_MEDIUM
        return LEVEL_MAINTHREAD

    def _create_thread(self, level, level_name, worker_name):
        thread = Thread(target=self._thread_run,
                        args=(level, level_name, worker_name),
                        name=worker_name)
        thread.daemon = True
        return thread

    #
    # Methods used by workers
    #

    def _thread_run(self, level, level_name, worker_name):
        while True:
            with level['condition']:
                task = self._get_task(level)
                if not task:
                    break
                self._pre_task_run(level, level_name, task, worker_name)
            task.run()
            with level['condition']:
                if task.can_retry() or task.state in {PENDING, PAUSED}:
                    level['waiting'].append(task)
                elif task.state == DONE or not task.can_retry():
                    # TODO: When to clear 'done' list?
                    task.set_state_condition(None)
                    level['done'].append(task)
                self._post_task_run(level, level_name, task, worker_name)
                self._clear_done_tasks(level, level_name)
        self._thread_stop(level, level_name, worker_name)

    def _get_task(self, level):
        task = None
        while not self._all_workers_stop_running:
            task_index = self._find_task_to_run(level['waiting'])
            if task_index > -1:
                task = level['waiting'].pop(task_index)
                break
            level['condition'].wait(level['timeout'])
        return task

    def _find_task_to_run(self, queue):
        # priority_task_index is for task in states:
        # CANCELLING, PAUSING, RESUMING
        # plus states: RUNNING and PENDING for mainthread tasks
        priority_task_index = -1
        pending_task_index = -1
        for index, task in enumerate(queue):
            if self._check_for_priority_task(task):
                priority_task_index = index
                break
            elif task.state == PENDING and pending_task_index == -1:
                if task.is_retrying():
                    if self._check_retry_condition(task):
                        pending_task_index = index
                elif self._check_periodic_condition(task):
                    pending_task_index = index
        if priority_task_index > -1:
            return priority_task_index
        return pending_task_index

    def _check_for_priority_task(self, task):
        # Manual retry of the task
        if (not task.retry_on_error
                and task.state == PENDING
                and task.is_retrying()):
            return True
        # Check if this is a main thread task
        if not task.run_in_thread:
            if task.state in {RUNNING, CANCELLING, PAUSING, RESUMING}:
                return True
        return (
            task.state in {CANCELLING, PAUSING, RESUMING}
            and self._check_periodic_condition(task)
        )

    def _check_periodic_condition(self, task):
        if not task.periodic:
            return True
        return time() - task.get_run_end_time() >= task.interval

    def _check_retry_condition(self, task):
        return time() - task.get_run_end_time() >= task.get_retry_interval()

    def _clear_done_tasks(self, level, level_name):
        delta = len(level['done']) - LEVEL_DONE_TASKS_LIMIT
        if delta > 0:
            for _ in range(delta):
                task = level['done'].pop(0)
                self.dispatch('on_task_item_remove',
                              self._create_task_item(task, level_name))

    def _main_thread_run(self, *args):
        level = self._levels[LEVEL_MAINTHREAD]
        task = self._main_thread_task
        if not task:
            task_index = self._find_task_to_run(level['waiting'])
            if task_index > -1:
                self._main_thread_task = \
                    task = level['waiting'].pop(task_index)
                self._pre_task_run(level, LEVEL_MAINTHREAD,
                                   task, _WORKER_MAINTHREAD_NAME)
        if task:
            task.run()
            if task.state == DONE:
                self._main_thread_task = None
                level['done'].append(task)
            elif task.state in {CANCELLED, CANCELLED_WITH_ERROR,
                                PAUSED, PENDING}:
                self._main_thread_task = None
                level['waiting'].append(task)
            if not self._main_thread_task:
                self._post_task_run(level, LEVEL_MAINTHREAD,
                                    task, _WORKER_MAINTHREAD_NAME)
        self._clear_done_tasks(level, LEVEL_MAINTHREAD)

    def _pre_task_run(self, level, level_name, task, worker_name):
        level['running'].append(task)
        worker_data = self._create_worker_data(task, datetime.now())
        level['worker_task'][worker_name] = worker_data
        self._dispatch_change_events(level_name, worker_name,
                                     task, worker_data)

    def _post_task_run(self, level, level_name, task, worker_name):
        level['running'].remove(task)
        worker_data = self._create_worker_data()
        level['worker_task'][worker_name] = worker_data
        self._dispatch_change_events(level_name, worker_name,
                                     task, worker_data)

    def _dispatch_change_events(self, level_name, worker_name, task,
                                worker_data):
        task_item = self._create_task_item(task, level_name, worker_name,
                                           worker_data['running_since'])
        self.mainthread_dispatch('on_task_item_change', task_item)
        worker_item = self._create_worker_item(worker_name, level_name,
                                               worker_data['task'],
                                               worker_data['running_since'])
        self.mainthread_dispatch('on_worker_item_change', worker_item)

    def _thread_stop(self, level, level_name, worker_name):
        with level['condition']:
            for index, task in enumerate(level['waiting'][:]):
                if task.state != CANCELLING:
                    task.set_state_condition(None)
                    level['waiting'].pop(index)
        while level['waiting']:
            task = None
            with level['condition']:
                if level['waiting']:
                    task = level['waiting'].pop(0)
            if task:
                task.set_state_condition(None)
                task.run()

    def _main_thread_stop(self):
        task = self._main_thread_task
        if task and task.state == CANCELLING:
            task.run()
        self._main_thread_task = None
        level = self._levels[LEVEL_MAINTHREAD]
        while level['waiting']:
            task = level['waiting'].pop(0)
            if task.state == CANCELLING:
                task.run()
        del level['running'][:]
        del level['done'][:]
        level['worker_task'].clear()

    def on_task_item_add(self, task_item):
        pass

    def on_task_item_remove(self, task_item):
        pass

    def on_task_item_change(self, task_item):
        pass

    def on_worker_item_change(self, worker_item):
        pass
