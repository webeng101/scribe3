from ia_scribe.tasks.book_tasks.reset import BookResetTask
from ia_scribe.uix.actions.book_task import BookTaskSchedulerPopupMixin
from ia_scribe.uix.components.poppers.popups import CheckBoxPopup


class DeleteBookActionMixin(BookTaskSchedulerPopupMixin):

    def __init__(self, **kwargs):
        super(DeleteBookActionMixin, self).__init__(**kwargs)
        self.message = 'Do you want to DELETE this book? \n\nYou cannot undo this ' \
                       'action. The images that you have captured will be ' \
                       'removed permanently.'
        checkbox_text = 'Also reset remote item' if 300 <= self.book.get_numeric_status() < 600 else ''
        self.popup_cls = CheckBoxPopup
        self.popup_args = {'checkbox_text': checkbox_text,
                           'extra': self.book,}
        self.book_command = 'do_move_to_trash'

    def do_action(self, *args, **kwargs):
        if self.popup.active:
            self.task_cls = BookResetTask
        super(DeleteBookActionMixin, self).do_action()

    def popup_setup_callback(self):
        self.popup.set_option_attrs(self.popup.OPTION_YES,
                                color_normal=[0.5, 0, 0, 1],
                                color_down=[1, 0, 0, 1])