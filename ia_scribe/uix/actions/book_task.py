from ia_scribe.tasks.book import BookTask, BookMultiTask
from ia_scribe.tasks.ui_handlers.generic import GenericUIHandler
from ia_scribe.uix.actions.generic import YesNoActionPopupMixin, Action, ColoredYesNoActionPopupMixin


class BookTaskSchedulerHelper(Action):
    """
    An action class that schedules a task about a Book.

    By default it is a BooKTask, in which case it is expected that a book_command
    parameter is provided. This can be also a list, in which case a BookMultiTask will be spawned.
    Alternatively, a different task type that consume Book can be scheduled
    by changing the value of task_cls.

    Two callbacks are provided: one that is called upon successful scheduling of the
    task (done_action_callback), and one that is called when the task finishes
    (done_task_callback)
    """
    task_handler = GenericUIHandler
    book = None
    task_scheduler = None
    task_cls = BookTask
    task_args = {}
    book_command = None
    done_action_callback = None
    done_task_callback = None

    def __init__(self, book, task_scheduler,
                 book_command=None,
                 done_action_callback=None,
                 done_task_callback=None,
                 **kwargs):
        self.book = book
        self.task_scheduler = task_scheduler
        self.done_action_callback = done_action_callback
        self.done_task_callback = done_task_callback
        self.book_command = book_command
        super(BookTaskSchedulerHelper, self).__init__(**kwargs)

    def do_action(self, *args, **kwargs):
        task_handler = self.create_task()
        self.submit_task(task_handler)
        if self.done_action_callback:
            popup = getattr(self, 'popup', None)
            self.done_action_callback(self.book, self.task_handler, popup)

    def create_task(self):
        task_config = {
            'task_type': self.task_cls,
            'book': self.book,
            'args': self.task_args,
        }
        if self.task_cls is BookTask:
            # Support lists of tasks by dispatching a BookMultiTask
            if type(self.book_command) is list:
                task_config['task_type'] = BookMultiTask
                task_config['scheduling_callback'] = self.task_scheduler.schedule
            task_config['command'] = self.book_command
        task_handler = self.task_handler(**task_config)
        task_handler.task.fbind('on_end', self.task_done_callback)
        return task_handler

    def submit_task(self, task_handler):
        self.task_scheduler.schedule(task_handler.task)

    def task_done_callback(self, task, *args):
        if self.done_task_callback:
            self.done_task_callback(self.book, task)


class BookTaskSchedulerPopupMixin(BookTaskSchedulerHelper, YesNoActionPopupMixin):
    """
    Multiple inheritance extraordinaire, this class is used to ask the user for confirmation
    with a yes or no action popup, and upon positive response, queue a book task for the
    appropriate method
    """

    def __init__(self, **kwargs):
        kwargs['title'] = kwargs.pop('title', 'Run book task') if not hasattr(self, 'title') else self.title
        kwargs['message'] = kwargs.pop('message', '') if not hasattr(self, 'message') else self.message
        super(BookTaskSchedulerPopupMixin, self).__init__(**kwargs)

    def display(self):
        create_popup_kwargs = {'popup_cls': self.popup_cls,
                               'title': self.title.format(self.book_command or self.task_cls.__name__,
                                                          self.book.name_human_readable()), }
        if self.message:
            create_popup_kwargs.update({'message': self.message, })
        create_popup_kwargs.update(self.popup_args)
        self.create_popup(**create_popup_kwargs)
        self.popup.bind(on_submit=self.on_submit)
        self.popup.open()


class GreenRedBookTaskSchedulerPopupMixin(BookTaskSchedulerPopupMixin, ColoredYesNoActionPopupMixin):
    """
    This class overrides popup setup to color the YES and NO buttons
    with green and red respectively.
    """
    pass