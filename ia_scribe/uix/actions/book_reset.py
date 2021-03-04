from ia_scribe.tasks.book_tasks.reset import BookResetTask
from ia_scribe.uix.actions.book_task import BookTaskSchedulerPopupMixin
from ia_scribe.uix.components.poppers.popups import QuestionPopup


class ResetBookActionMixin(BookTaskSchedulerPopupMixin):
    def __init__(self, **kwargs):
        super(ResetBookActionMixin, self).__init__(**kwargs)
        self.message = '[size=24]Are you [u]sure[/u] you want to [b]reset[/b] this book?[/size]' \
                  '\n\nThis will:\n' \
                  '- [b]Delete this local book [b]from the scribe[/b] and all data contained therein[/b], ' \
                  'including captured leafs, metadata and logs.\n' \
                  '- Leave the contents of the item on archive.org untouched.\n' \
                  '- [b]Unclaim the identifier[/b] for reuse with Scribe3\n\n' \
                  'This action cannot be undone. Proceed?'
        self.popup_cls = QuestionPopup
        self.popup_args = {'message_halign': 'left',
                           'text_no': 'Yes, reset',
                           'text_yes': 'No',
                           'size': (550, 330)}
        self.task_cls = BookResetTask

    # Since YES and NO are inverted (so that NO is selected by default), override
    def on_submit(self, popup, option, *args):
        if option == self.popup.OPTION_NO:
            self.popup.dismiss(animation=False)
            self.do_action()
