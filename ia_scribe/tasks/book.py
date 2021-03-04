from ia_scribe.tasks.task_base import TaskBase
from ia_scribe.tasks.meta import MetaSchedulerTask
from ia_scribe.book.automata import move_along

# Run a method of a Book object as a task
class BookTask(TaskBase):
    def __init__(self, **kwargs):
        self._priority = 'high'
        self.book = kwargs['book']
        self.command = kwargs['command']
        self.args = kwargs.get('args', None)
        self.callbacks = kwargs.get('callbacks', [])
        super(BookTask, self).__init__(logger=kwargs['book'].logger, **kwargs)

    def create_pipeline(self):
        return [
            self._get_callable,
            self._sanitize,
            self._run,
            self._call_back,
            self._set_message,
        ]

    def _get_callable(self):
        self.dispatch_progress('Loading command')
        self.callable = getattr(self.book, self.command)

    def _sanitize(self):
        self.dispatch_progress('Sanitizing')
        if not self.args:
            self.args = []
        if not self.callbacks:
            self.callbacks = []

    def _run(self):
        self.dispatch_progress('Running {} on {} with args {}'.format(self.command, self.book, self.args))
        self.res = self.callable(*self.args)

    def _call_back(self):
        self.dispatch_progress('Dispatching callbacks')
        for callback in self.callbacks:
            callback(self.res)

    def _set_message(self):
        self.done_message = '{} on {}'.format(self.command, self.book)

class BookMultiTask(MetaSchedulerTask):
    def __init__(self, **kwargs):
        super(BookMultiTask, self).__init__(**kwargs)
        self._book = kwargs['book']
        self._commands = kwargs['command']

    def _fill_list(self):
        for command in self._commands:
            task = BookTask(book=self._book,
                            command=command)
            self._tasks_list.append(task)

# Run the book engine as a task
class MoveAlongBookTask(TaskBase):
    def __init__(self, **kwargs):
        super(MoveAlongBookTask, self).__init__(**kwargs)
        self._priority = 'low'
        self._book = kwargs['book']

    def create_pipeline(self):
        return [
            self._move_along,
        ]

    def _move_along(self):
        self.dispatch_progress('{}'.format(self._book))
        try:
            ''' Passing True to set_lock makes this function wait until the lock is
            freed so that the subsequent move_alongs can be executed. The downside is that
            this may keep more than one worker busy on the same book. 
            '''
            if self._book.set_lock(True):
                log, exception = move_along(self._book)
            else:
                raise Exception('Could not run move_along '
                                'on {} because it was locked.'.format(self._book))
            self._book.set_log(log)
            if exception:
                raise exception
        except Exception as e:
            self._book.logger.error(str(e))
            self._book.raise_exception(e, "Processing error")
        finally:
            self._book.logger.info('Releasing lock on {}'.format(self._book))
            self._book.release_lock()
            self._book.update_message(None)

# Schedule move alongs for all books
class MoveAlongSchedulerTask(MetaSchedulerTask):

    def __init__(self, **kwargs):
        self._library = kwargs.pop('library')
        super(MoveAlongSchedulerTask, self).__init__(**kwargs)
        self._priority = 'medium'

    def _fill_list(self):
        for book in self._library.get_all_books():
            if not book.is_locked():
                task = MoveAlongBookTask(book=book)
                self._tasks_list.append(task)

