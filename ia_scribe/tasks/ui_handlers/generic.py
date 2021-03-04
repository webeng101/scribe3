from ia_scribe.uix.components.poppers.popups import InfoPopup
from ia_scribe.tasks.ui_handlers.ui_handler import TaskUIHandler


class GenericUIHandler(TaskUIHandler):
    def __init__(self, task_type, **kwargs):
        self.task_class = task_type
        self.task = self.task_class(**kwargs)
        super(GenericUIHandler, self).__init__(**kwargs)

    def _on_task_end(self, task):
        self.progress_popup.dismiss()
        if task.error:
            # AuthenticationError does not have "message" attribute
            msg = '{}'.format(getattr(task.error, 'message', str(task.error)))
            if hasattr(task, 'command'):
                msg += ' while running {}'.format(task.command)

            popup = InfoPopup(
                title='{} error'.format(task.name),
                message=msg,
                auto_dismiss=False
            )
            popup.bind(on_submit=popup.dismiss)
            popup.open()