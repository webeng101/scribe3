from ia_scribe.tasks.task_base import TaskBase


class ServiceBase(TaskBase):

    def __init__(self, **kwargs):
        self.task_scheduler = None
        kwargs.setdefault('periodic', True)
        kwargs.setdefault('interval', 300)
        super(ServiceBase, self).__init__(**kwargs)
