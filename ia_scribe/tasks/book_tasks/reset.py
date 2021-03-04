from os.path import join
from os import remove
from ia_scribe.ia_services.iabdash import push_event
from ia_scribe.book.metadata import get_metadata, set_metadata
from ia_scribe.tasks.task_base import TaskBase
from ia_scribe.tasks.book_tasks.remote import ChangeRepubStateTask
from ia_scribe.book.book import RepubState
from ia_scribe.ia_services.btserver import get_ia_session

class BookResetTask(TaskBase):

    ALLOWED_REPUB_STATE = RepubState.scan_started.value
    TARGET_REPUB_STATE = RepubState.stub_ready_for_scanning.value
    ABLE_TO_CHANGE_REPUB_STATE = False

    def __init__(self, **kwargs):
        self.book = kwargs['book']
        super(BookResetTask, self).__init__(logger=kwargs['book'].logger, **kwargs)

    def create_pipeline(self):
        return [
            self._verify_preconditions,
            ChangeRepubStateTask(book=self.book,
                                 target_repub_state=self.TARGET_REPUB_STATE) if self.ABLE_TO_CHANGE_REPUB_STATE else lambda:None,
            self.delete_local_book,
            self._send_telemetry,
        ]

    def _verify_preconditions(self):
        self.dispatch_progress('Verifying preconditions')
        if not self.book.has_identifier():
            self.ABLE_TO_CHANGE_REPUB_STATE = False
        item = get_ia_session().get_item(self.book.identifier)
        if not item.exists:
            self.ABLE_TO_CHANGE_REPUB_STATE = False
        if item.metadata.get('repub_state') != '{}'.format(self.ALLOWED_REPUB_STATE):
            self.ABLE_TO_CHANGE_REPUB_STATE = False
        self.ABLE_TO_CHANGE_REPUB_STATE = True
        return True

    def delete_local_book(self):
        self.dispatch_progress('Nuking book')
        self.book.force_delete = True
        self.book.do_move_to_trash()

    def _send_telemetry(self):
        self.dispatch_progress('Sending telemetry')
        payload = {'book': self.book.as_dict(),
                   }
        push_event('tts-book-reset', payload, 'book', self.book.uuid)


