from ia_scribe.tasks.task_base import CANCELLED
from ia_scribe.uix.components.poppers.popups import (
    InfoPopup,
    QuestionPopup,
    ProgressPopup,
)


class TaskUIHandler(object):

    task = None
    end_handler = None

    def __init__(self, **kwargs):
        self.end_handler = kwargs.get('end_handler')
        self.progress_popup = ProgressPopup()
        self._setup()

    def _setup(self):
        self.task.fbind('on_start', self.progress_popup.open)
        self.task.fbind('on_progress', self._on_task_progress)
        self.task.fbind('on_end', self._on_task_end)

    def _on_task_end(self, task):
        self.progress_popup.dismiss()

        if self.end_handler:
            self.end_handler(self, task)

        if self.task.error:
            popup = InfoPopup(
                title='Error',
                message='[b]{}[/b]'.format(
                    self.task.error),
                auto_dismiss=False,
            )
            popup.bind(on_submit=popup.dismiss)
            popup.open()

    def _on_task_progress(self, task, report):
        self.progress_popup.message = report.get('message', None) or ''
        self.progress_popup.progress = report.get('progress', 0)

        if report.get('input_needed', False):
            self._ask_for_input(report)

    def _ask_for_input(self, report):
        if report.get('input_type') == 'yes_no_decision':
            popup = QuestionPopup(
                title=report.get('title', 'Question'),
                message=report.get('popup_body_message', 'Yes or no?'),
                text_yes=report.get('text_yes', 'Yes'),
                text_no=report.get('text_no', 'No'),
                auto_dismiss=False,
            )
            popup.bind(on_submit=self._on_input_submit)
            popup.open()
        elif report.get('input_type') == 'yes_no_cancel_decision':
            raise NotImplementedError()
        elif report.get('input_type') == 'alphanumeric_input':
            raise NotImplementedError()

    def _on_input_submit(self, popup, value):
        popup.dismiss()
        if self.task.state == CANCELLED:
            return
        else:
            self.task.user_input = value
            self.task.resume()
