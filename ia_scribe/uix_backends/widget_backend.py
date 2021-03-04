from kivy.event import EventDispatcher
from kivy.logger import Logger


class WidgetBackend(EventDispatcher):

    EVENT_INIT = 'on_init'
    EVENT_RESET = 'on_reset'
    EVENT_ERROR = 'on_error'
    EVENT_TASK_START = 'on_task_start'
    EVENT_TASK_END = 'on_task_end'
    EVENT_TASK_PROGRESS = 'on_task_progress'

    __events__ = (EVENT_ERROR, EVENT_INIT, EVENT_RESET,
                  EVENT_TASK_START, EVENT_TASK_END, EVENT_TASK_PROGRESS)

    def __init__(self, **kwargs):
        self._initialized = False
        self._tasks = []
        self.logger = Logger
        super().__init__(**kwargs)

    def is_initialized(self):
        return self._initialized

    def init(self):
        self._initialized = True
        self.dispatch(self.EVENT_INIT)

    def reset(self):
        self.dispatch(self.EVENT_RESET)
        self._initialized = False

    def reinit(self):
        name = type(self).__name__
        self.logger.info('{}: Reinit start'.format(name))
        self.reset()
        self.init()
        self.logger.info('{}: Reinit end'.format(name))

    def dispatch(self, event_name, *args, **kwargs):
        if self._initialized:
            return super(WidgetBackend, self)\
                .dispatch(event_name, *args, **kwargs)

    def _create_task(self, task_cls, **kwargs):
        task = task_cls(**kwargs)
        task.fbind('on_start', self._on_task_start)
        task.fbind('on_end', self._on_task_end)
        task.fbind('on_progress', self._on_task_progress)
        return task

    def _on_task_start(self, task):
        self.dispatch(self.EVENT_TASK_START)

    def _on_task_progress(self, task, report):
        self.dispatch(self.EVENT_TASK_PROGRESS, report)

    def _on_task_end(self, task):
        task.funbind('on_start', self._on_task_start)
        task.funbind('on_end', self._on_task_end)
        task.funbind('on_progress', self._on_task_progress)
        self.dispatch(self.EVENT_TASK_END)

    def on_init(self):
        self.logger.info('{}: Initialized'.format(type(self).__name__))

    def on_reset(self):
        self.logger.info('{}: Reset'.format(type(self).__name__))

    def on_error(self, message):
        pass

    def on_task_start(self):
        pass

    def on_task_end(self):
        pass

    def on_task_progress(self, report):
        pass
