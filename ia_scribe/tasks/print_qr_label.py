import cups
from os.path import join, exists

from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.libraries.qrcode_label import BookLabel
from ia_scribe.scribe_globals import PRINT_LABEL_FILENAME, DEFAULT_PRINTER_NAME
from ia_scribe.tasks.task_base import TaskBase
from ia_scribe.utils import get_string_value_if_list
from ia_scribe.tasks.book_tasks.identifier import make_identifier

config = Scribe3Configuration()


class PrintQRLabelTask(TaskBase):

    def __init__(self, **kwargs):
        super(PrintQRLabelTask, self).__init__(**kwargs)
        self.book_path = kwargs['book_path']
        self.text = kwargs['text']
        self.metadata = kwargs['metadata']
        self.identifier = kwargs['identifier']
        self._target_title = None
        self._target_creator = None

    def create_pipeline(self):
        return [
            self._verify_book_path,
            self._ensure_identifier,
            self._save_label_image,
            self._print_on_physical_printer
        ]

    def _verify_book_path(self):
        self.dispatch_progress('Verifying that book path exists')
        if not (self.book_path and exists(self.book_path)):
            self.error = ValueError(
                'Book path does not exists.\n'
                'You should create new book before printing a QR label.'
            )

    def _ensure_identifier(self):
        self.dispatch_progress('Ensuring identifier')
        metadata = self.metadata or {}
        creator = metadata.get('creator', None) or 'unset'
        title = metadata.get('title', None) or 'unset'
        volume = metadata.get('volume', None) or '00'
        if not self.identifier:
            self.dispatch_progress('Creating new identifier')
            self.identifier = identifier = make_identifier(
                title,
                volume,
                get_string_value_if_list(metadata, 'creator') or 'unset'
            )
            self.dispatch_progress('Created new identifier: {}'
                                   .format(identifier))
        self._target_title = title
        self._target_creator = \
            creator if isinstance(creator, list) else [creator]

    def _save_label_image(self):
        self.dispatch_progress('Saving label image')
        self._label_path = path = join(self.book_path, PRINT_LABEL_FILENAME)
        label_obj = BookLabel(self.identifier,
                              self._target_title,
                              self._target_creator)
        label_raw = label_obj.create_label(self.text)
        label_raw.save(path)
        self.dispatch_progress('Saved QR label')

    def _print_on_physical_printer(self):
        self.dispatch_progress('Printing')
        label_path = self._label_path
        printer_name = config.get('printer', DEFAULT_PRINTER_NAME)
        conn = cups.Connection()
        conn.printFile(printer_name, label_path, '', {})
        self.dispatch_progress('Printed qr label')
