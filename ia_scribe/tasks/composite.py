from ia_scribe.tasks.task_base import TaskBase
from ia_scribe.tasks.task_base import CANCELLED
from ia_scribe.tasks.print_slip import MakeSlipTask, PrintSlipTask
from ia_scribe.tasks.ia_identifier import CreateModernItemTask
from ia_scribe.tasks.book import BookTask
from ia_scribe.uix.components.poppers.popups import ThreeOptionsQuestionPopup


class MakeAndPrintSlipTask(TaskBase):
    _slip_cache = {}

    def __init__(self, **kwargs):
        kwargs['run_in_thread'] = False
        kwargs['dispatch_on_main_thread'] = False
        self._book = kwargs['book']
        self._type = kwargs['type']
        self._slip_metadata = kwargs['slip_metadata']
        self._transition = kwargs.get('transition')
        super(MakeAndPrintSlipTask, self).__init__(logger=kwargs['book'].logger, **kwargs)

    def create_pipeline(self):
        pipeline = [
            MakeSlipTask(book=self._book,
                         type=self._type,
                         slip_metadata=self._slip_metadata),
            PrintSlipTask(book=self._book,
                          type=self._type),
        ]

        if self._transition:
            transition_task = BookTask(book=self._book,
                                       command=self._transition)
            pipeline.append(transition_task)

        return pipeline

    def _handle_sub_task_error(self, sub_task, index, error):
        return False


class MakeReserveAndPrintSlipTask(TaskBase):
    _slip_cache = {}

    def __init__(self, **kwargs):
        kwargs['run_in_thread'] = False
        kwargs['dispatch_on_main_thread'] = False
        self._book = kwargs['book']
        self._type = kwargs['type']
        self._force = kwargs['force'] \
            if 'skip_metadata' in kwargs\
            else False
        self._slip_metadata = kwargs['slip_metadata'] \
            if 'slip_metadata' in kwargs \
            else {}
        self._transition = kwargs.get('transition')
        super(MakeReserveAndPrintSlipTask, self).__init__(logger=kwargs['book'].logger, **kwargs)

    def create_pipeline(self):
        pipeline = [
            MakeSlipTask(book=self._book,
                         type = self._type,
                         slip_metadata = self._slip_metadata),
            CreateModernItemTask(book = self._book,
                                 force = self._force),
            PrintSlipTask(book=self._book,
                          type = self._type),
        ]

        if self._transition:
            transition_task = BookTask(book=self._book,
                                       command=self._transition)
            pipeline.append(transition_task)

        return pipeline

    def _handle_sub_task_error(self, sub_task, index, error):
        return False

    def _on_make_reserve_print_slip_progress(self, task, data):
        if data.get('input_needed', False):
            popup = ThreeOptionsQuestionPopup(
                title=data.get('title', 'What to do?'),
                message=data.get('popup_body_message', 'A problem occurred'),
                text_yes=data.get('text_yes', 'Yes'),
                text_no=data.get('text_no', 'No'),
                text_else=data.get('text_else', 'Cancel'),
                auto_dismiss=False,
            )
            popup.extra = {'parent_task': task, 'sub_task': data.get('task')}
            popup.bind(on_submit=self._on_make_reserve_print_slip_progress_popup_submit)
            popup.open()

    def _on_make_reserve_print_slip_progress_popup_submit(self, popup, value):
        popup.dismiss()
        task = popup.extra.get('sub_task')
        if task.state == CANCELLED:
            # In general, task can get cancelled by another UI
            return
        else:
            task.user_input = value
            task.resume()
