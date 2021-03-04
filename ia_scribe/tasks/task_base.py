from datetime import datetime
from functools import partial
from threading import Lock
from time import time

from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.logger import Logger

PENDING = 'pending'
RUNNING = 'running'
PAUSING = 'pausing'
PAUSED = 'paused'
RESUMING = 'resuming'
CANCELLING = 'cancelling'
CANCELLED = 'cancelled'
CANCELLED_WITH_ERROR = 'cancelled_with_error'
DONE = 'done'
ALL_STATES = {
    PENDING, RUNNING, PAUSING, PAUSED, RESUMING, CANCELLING, CANCELLED,
    CANCELLED_WITH_ERROR, DONE
}

_NUMBER_TYPE = (int, float)


class TaskBase(EventDispatcher):

    __events__ = ('on_start', 'on_progress', 'on_state', 'on_end')

    def _get_state(self):
        return self._state

    state = property(_get_state)

    def _get_last_report(self):
        return self._last_report

    last_report = property(_get_last_report)

    def _get_first_start(self):
        return self._first_start

    first_start = property(_get_first_start)

    def _get_started_at(self):
        return self._started_at

    started_at = property(_get_started_at)

    def _get_ended_at(self):
        return self._ended_at

    ended_at = property(_get_ended_at)

    def _get_cycle_count(self):
        return self._cycle_count

    cycle_count = property(_get_cycle_count)

    def _get_retry_count(self):
        return self._retry_count

    retry_count = property(_get_retry_count)

    def __new__(cls, *args, **kwargs):
        if 'interval' in kwargs:
            if kwargs['interval'] is None and kwargs.get('periodic', False):
                raise ValueError('Cannot instantiate a periodic task without an interval.')
            elif not isinstance(kwargs['interval'], _NUMBER_TYPE):
                raise TypeError(
                    'Keyword "interval" has incorrect type, expected {} got {}'
                    .format(_NUMBER_TYPE, type(kwargs['interval']))
                )
        if 'retry_interval' in kwargs \
                and not isinstance(kwargs['retry_interval'], _NUMBER_TYPE):
            raise TypeError(
                'Keyword "retry_interval" has incorrect type, '
                'expected {} got {}'
                .format(_NUMBER_TYPE, type(kwargs['retry_interval']))
            )
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, **kwargs):
        self.dispatch_on_main_thread = \
            kwargs.pop('dispatch_on_main_thread', True)
        self.run_in_thread = kwargs.pop('run_in_thread', True)
        self.interval = kwargs.pop('interval', 30.0)
        self.periodic = kwargs.pop('periodic', False)
        self.logger = kwargs.pop('logger', Logger)
        self.done_message = kwargs.pop('done_message', 'Done')
        self.name = kwargs.pop('name', type(self).__name__)
        self.error = None
        self.retry_on_error = kwargs.pop('retry_on_error', False)
        self.retry_interval = kwargs.pop('retry_interval', 30.0)
        self.retry_limit = kwargs.pop('retry_limit', 3)
        self._retry_count = 0
        self._cycle_count = 0
        self._parent = None
        self._root_task = None
        self._current_index = 0
        self._target_index = -1
        self._state_lock = Lock()
        self._state_condition = None
        self._state = PENDING
        self._run_start_time = 0
        self._run_end_time = 0
        self._started_at = None
        self._ended_at = None
        self._first_start = True
        self._sub_task_run_once = False
        self._stay_on_current_step = False
        self._last_report = {}
        super(TaskBase, self).__init__()
        self._pipeline = self._adjust_pipeline(self.create_pipeline())

    def create_pipeline(self):
        raise NotImplementedError()

    def pause(self):
        return self._change_state_to(PAUSING, {PENDING, RUNNING, RESUMING})

    def resume(self):
        return self._change_state_to(RESUMING, {PAUSED})

    def cancel(self):
        condition_states = {PENDING, RUNNING, PAUSING, PAUSED, RESUMING}
        return self._change_state_to(CANCELLING, condition_states)

    def can_retry(self):
        # Enable retry only when user cancel task or
        # when task is cancelled due to an error and is a periodic task.
        # For these 2 cases user can retry the task.
        if self.state == CANCELLED:
            return True
        return self.state == CANCELLED_WITH_ERROR and self.periodic

    def retry(self):
        success = False
        with self._state_lock:
            if self.can_retry():
                self._ended_at = None
                self._retry_count = 1
                self._reset_without_lock()
                success = True
        return success

    def reset(self, state=PENDING, skip_setting_state=False):
        with self._state_lock:
            self._reset_without_lock(state, skip_setting_state)

    def stop(self):
        with self._state_lock:
            current_index = self._current_index
            self._current_index = len(self._pipeline)
            self._ended_at = datetime.now()
            self._retry_count = 0
            self._set_state_without_lock(DONE)
            for sub_task in self._pipeline[current_index:]:
                if isinstance(sub_task, TaskBase) and sub_task.state != DONE:
                    sub_task.stop()

    def _seek(self, index):
        with self._state_lock:
            current_index = self._current_index
            if index > current_index:
                for sub_task in self._pipeline[current_index:index]:
                    if isinstance(sub_task, TaskBase):
                        sub_task.stop()
            elif index < current_index:
                for sub_task in self._pipeline[index:current_index + 1]:
                    if isinstance(sub_task, TaskBase):
                        sub_task.reset()

    def _reset_without_lock(self, state=PENDING, skip_setting_state=False):
        self.error = None
        self._current_index = 0
        self._sub_task_run_once = False
        self._stay_on_current_step = False
        if not skip_setting_state:
            self._set_state_without_lock(state)
        for sub_task in self._pipeline:
            if isinstance(sub_task, TaskBase):
                sub_task.reset()

    def _change_state_to(self, target_state, condition_states):
        this = self.get_root_task()
        locks = []
        success = False
        while isinstance(this, TaskBase):
            locks.append(this._state_lock)
            locks[-1].acquire()
            if this.state in condition_states:
                this._set_state_without_lock(target_state)
                success = True
            else:
                break
            try:
                this = this._pipeline[this._current_index]
            except IndexError:
                this = None
        while locks:
            lock = locks.pop()
            lock.release()
        return success

    def compute_progress(self):
        result = self._current_index
        stack = self._pipeline[:]
        pipeline_size = 0
        while stack:
            sub_task = stack.pop()
            if isinstance(sub_task, TaskBase):
                result += sub_task._current_index
                stack.extend(sub_task._pipeline)
            pipeline_size += 1
        return 1.0 * result / pipeline_size if pipeline_size else 0.0

    def get_run_start_time(self):
        return self._run_start_time

    def get_run_end_time(self):
        return self._run_end_time

    def get_root_task(self):
        if self._root_task:
            return self._root_task
        this = self
        while this._parent:
            this = this._parent
        self._root_task = this
        return this

    def get_retry_interval(self):
        return self.retry_interval

    def is_retrying(self):
        return self._retry_count > 0

    def set_state_condition(self, condition):
        self._state_condition = condition

    def run(self):
        self._run_start_time = time()
        self._sub_task_run_once = False
        while True:
            if self._inspect_state_before_sub_task_run():
                break
            index = self._current_index
            sub_task = self._get_current_sub_task()
            try:
                sub_task()
                index += 1
            except Exception as e:
                if not self._safe_handle_sub_task_error(sub_task, index, e):
                    index = max(0, index - 1)
                    self.error = e
                    if self._parent:
                        self._sub_task_run_once = True
                        raise
                    else:
                        self.logger.exception('')
                else:
                    index += 1
                    self._seek(index)
                    self._current_index = index
                    self._stay_on_current_step = False
                    self.logger.exception('')
            self._sub_task_run_once = True
            if not self._should_stay_on_current_step():
                if self._target_index > -1:
                    if self._target_index != index:
                        index = self._target_index
                        self._seek(index)
                    self._target_index = -1
                self._current_index = index
        self._run_end_time = time()

    def _should_stay_on_current_step(self):
        if self._stay_on_current_step:
            return True
        sub_task = self._pipeline[self._current_index]
        if isinstance(sub_task, TaskBase):
            if sub_task.state == DONE:
                return False
            elif sub_task.state == PAUSED:
                return True
            elif not self.get_root_task().run_in_thread:
                return True
            return sub_task._should_stay_on_current_step()
        return False

    def _get_current_sub_task(self):
        sub_task = self._pipeline[self._current_index]
        if isinstance(sub_task, TaskBase):
            return sub_task.run
        return sub_task

    def _inspect_state_before_sub_task_run(self):
        should_break = False
        with self._state_lock:
            if self.error:
                self._cancel(CANCELLED_WITH_ERROR)
                should_break = True
            elif self.state == CANCELLING:
                self._cancel(CANCELLED)
                should_break = True
            elif self.state == PAUSING:
                self._set_state_without_lock(PAUSED)
                should_break = True
            elif self._is_task_done_successfully():
                self._done_cycle() if self.periodic else self._done()
                should_break = True
            elif self.state in {PENDING, RESUMING}:
                self._start() if self._first_start else self._start_cycle()
            elif self._has_run_main_thread_sub_task():
                # Main thread task, sub-tasks are run per frame
                should_break = True
        return should_break

    def _notify_state_change(self):
        condition = self._state_condition
        if condition:
            with condition:
                condition.notify()

    def _set_state_without_lock(self, state):
        if self._state != state:
            self._state = state
            self._notify_state_change()
            self.safe_dispatch('on_state', state)

    def _is_task_done_successfully(self):
        return self._current_index == len(self._pipeline)

    def _has_run_main_thread_sub_task(self):
        root = self.get_root_task()
        if self._parent:
            if not root.run_in_thread and self._sub_task_run_once:
                return True
        return not self.run_in_thread and self._sub_task_run_once

    def _start(self):
        self._first_start = False
        self._current_index = 0
        self._started_at = datetime.now()
        self._set_state_without_lock(RUNNING)
        self.safe_dispatch('on_start')

    def _start_cycle(self):
        self._set_state_without_lock(RUNNING)

    def _done(self):
        self.dispatch_progress(self.done_message)
        self._ended_at = datetime.now()
        self._retry_count = 0
        self._set_state_without_lock(DONE)
        self.safe_dispatch('on_end')

    def _done_cycle(self):
        self.dispatch_progress(self.done_message)
        self._reset_without_lock()
        self._cycle_count += 1
        self._retry_count = 0
        self.dispatch_progress('Waiting for %.0f seconds' % self.interval)

    def _cancel(self, state):
        self._ended_at = datetime.now()
        self._set_state_without_lock(state)
        if state == CANCELLED_WITH_ERROR and self.retry_on_error:
            if self._retry_count < self.retry_limit:
                self._retry_count += 1
                self._ended_at = None
                self._reset_without_lock()
                self.dispatch_progress('Retrying task in %.0f seconds'
                                       % self.get_retry_interval())
            else:
                self.safe_dispatch('on_end')
        else:
            self.safe_dispatch('on_end')

    def _adjust_pipeline(self, pipeline):
        for sub_task in pipeline:
            if isinstance(sub_task, TaskBase):
                sub_task._parent = self
                sub_task.retry_on_error = False
                sub_task.dispatch_on_main_thread = False
                sub_task.periodic = False
        return pipeline

    def _safe_handle_sub_task_error(self, sub_task, index, error):
        try:
            return self._handle_sub_task_error(sub_task, index, error)
        except Exception:
            self._target_index = -1
            self.logger.exception('{}: Failed to handle error in step {}'
                                  .format(self.name, self._current_index))
            return False

    def _handle_sub_task_error(self, sub_task, index, error):
        return False

    def safe_dispatch(self, event_name, *args, **kwargs):
        try:
            self.handle_event(event_name, *args, **kwargs)
        except Exception:
            self.logger.exception('Failed to handle event: {} '
                                  'with args = {}; kwargs = {}'
                                  .format(event_name, args, kwargs))
        if self._parent and event_name != 'on_progress':
            return
        root = self.get_root_task()
        if event_name == 'on_progress':
            args[0]['progress'] = root.compute_progress()
            root._last_report = args[0]
        root._log_event(event_name, *args, **kwargs)
        if root.dispatch_on_main_thread:
            method = partial(root.dispatch_callback, event_name, args, kwargs)
            Clock.schedule_once(method)
        else:
            return root.dispatch(event_name, *args, **kwargs)

    def dispatch_callback(self, event_name, args, kwargs, dt):
        self.dispatch(event_name, *args, **kwargs)

    def dispatch_progress(self, message, **kwargs):
        report = {'message': message}
        report.update(kwargs)
        self.safe_dispatch('on_progress', report)

    def handle_event(self, event_name, *args, **kwargs):
        pass

    def _log_event(self, event_name, *args, **kwargs):
        if self.logger:
            if event_name == 'on_progress':
                self.logger.debug('{}: Progress: {}'
                                  .format(self.name, (args[0])))
            elif event_name == 'on_state':
                self.logger.debug('{}: State: {}'.format(self.name, args[0]))
            elif event_name == 'on_start':
                self.logger.info('{}: Start'.format(self.name))
            elif event_name == 'on_end':
                self.logger.info('{}: End'.format(self.name))

    def on_start(self):
        pass

    def on_progress(self, report):
        pass

    def on_state(self, state):
        pass

    def on_end(self):
        pass
