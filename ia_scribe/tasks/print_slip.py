import cups
from os.path import join, exists

from ia_scribe import scribe_globals
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.scribe_globals import DEFAULT_PRINTER_NAME
from ia_scribe.tasks.task_base import TaskBase
from ia_scribe.uix.slips.book_slips import BookScannedSlip, BookRejectedSlip, BookDoNotWantSlip
from ia_scribe.ia_services.ingestion_adapters import put_metric

config = Scribe3Configuration()

SCANNED_SLIP = 1
SCANNED_NO_MARC_SLIP = 2
REJECTED_DO_NOT_WANT_SLIP = 3
REJECTED_CAN_NOT_SCAN_SLIP = 4

SLIP_WIDGET_CLASS = {
    SCANNED_SLIP: BookScannedSlip,
    SCANNED_NO_MARC_SLIP: BookScannedSlip,
    REJECTED_DO_NOT_WANT_SLIP: BookDoNotWantSlip,
    REJECTED_CAN_NOT_SCAN_SLIP: BookRejectedSlip
}
SLIP_IMAGE_NAMES = {
    SCANNED_SLIP: 'scanned_slip',
    SCANNED_NO_MARC_SLIP: 'scanned_no_marc_slip',
    REJECTED_DO_NOT_WANT_SLIP: 'rejected_do_not_want_slip',
    REJECTED_CAN_NOT_SCAN_SLIP: 'rejected_tight_margins_slip'
}

class MakeSlipTask(TaskBase):

    _slip_cache = {}

    def __init__(self, **kwargs):
        kwargs['run_in_thread'] = False
        kwargs['dispatch_on_main_thread'] = False
        self._book = kwargs['book']
        super(MakeSlipTask, self).__init__(logger=kwargs['book'].logger, **kwargs)
        self._slip_type = kwargs['type']
        self._slip_metadata = kwargs['slip_metadata']
        self._book_path = self._book.path
        self._metadata = self._book.metadata
        self._slip_widget = None
        self._slip_image = None
        self._slip_filename = None
        self._isbn = None

    def create_pipeline(self):
        return [
            self._get_isbn_file,
            self._load_identifier,
            self._get_slip_widget_from_cache,
            self._update_slip_widget,
            self._create_slip_image,
            self._return_slip_widget_to_cache,
            self._save_slip_image_to_disk,
            self._save_slip_metadata_to_disk,
            self._send_metrics,
        ]

    def _get_isbn_file(self):
        self.dispatch_progress('Loading ISBN')
        target = join(self._book.path, scribe_globals.ORIGINAL_ISBN_FILENAME)
        if exists(target):
            with open(target, 'r') as f:
                self._isbn = f.read()
        else:
            if 'scribe3_search_id' in self._metadata:
                self._isbn = self._metadata['scribe3_search_id']
            elif ('isbn' in self._metadata \
                    and len(self._metadata['isbn']) != 0) :
                candidate_isbn = self._metadata['isbn']
                if type(candidate_isbn) == list:
                    self._isbn = candidate_isbn[0]
                else:
                    self._isbn = candidate_isbn
            elif 'isbn' in self._slip_metadata \
                    and len(self._slip_metadata['isbn']) != 0:
                self._isbn = self._slip_metadata['isbn']
            elif 'selector' in self._slip_metadata \
                    and len(self._slip_metadata['selector']) != 0:
                self._isbn = self._slip_metadata['selector']
            else:
                self.logger.info('no selector found - printing from identifier')
                self._isbn = 'No selector'
        self.dispatch_progress('Loaded ISBN {}'.format(self._isbn))

    def _load_identifier(self):
        self._metadata['identifier'] = self._book.identifier

    def _get_slip_widget_from_cache(self):
        slip_type = self._slip_type
        slip_widget = self._slip_cache.pop(slip_type, None)
        if not slip_widget:
            slip_widget = SLIP_WIDGET_CLASS[slip_type]()
        self._slip_widget = slip_widget

    def _update_slip_widget(self):
        slip_widget = self._slip_widget
        slip_widget._isbn = self._isbn
        self._metadata.update(self._slip_metadata)
        slip_widget.set_metadata(self._metadata)

    def _create_slip_image(self):
        self.dispatch_progress('Creating slip image')
        self._slip_image = self._slip_widget.create_image()
        self.dispatch_progress('Created slip image')

    def _return_slip_widget_to_cache(self):
        self._slip_cache[self._slip_type] = self._slip_widget
        self._slip_widget = None

    def _save_slip_image_to_disk(self):
        self.dispatch_progress('Saving slip image to disk')
        name = SLIP_IMAGE_NAMES[self._slip_type]
        if exists(self._book_path):
            self._slip_filename = filename = join(self._book_path, name + '.png')
        else:
            self._slip_filename = filename = join('/tmp/', '{}_{}.png'.format(self._isbn, name))

        self._slip_image.save(filename)
        self.logger.info('PrintSlipTask: Saved slip image to: {}'
                         .format(filename))
        self.dispatch_progress('Slip image saved. Reserving identifier...')

    def _save_slip_metadata_to_disk(self):
        self._book.set_slip_metadata(self._slip_type, self._slip_metadata)

    def _send_metrics(self):
        payload = {
            'path': self._book_path,
            'search_term': self._isbn,
            'scanner': self._metadata.get('scanner', ''),
            'boxid': self._metadata.get('boxid', ''),
            'identifier': self._metadata.get('identifier', ''),
            'operator': self._metadata.get('operator', ''),
        }
        put_metric('scribe3.book.slip_created', self._slip_type, payload)

class PrintSlipTask(TaskBase):

    def __init__(self, **kwargs):
        kwargs['run_in_thread'] = False
        kwargs['dispatch_on_main_thread'] = False
        super(PrintSlipTask, self).__init__(logger=kwargs['book'].logger, **kwargs)
        self._book = kwargs['book']
        self._slip_type = kwargs['type']

    def create_pipeline(self):
        return [
            self._load_slip_image,
            self._print_on_physical_printer,
            self._send_metrics,
        ]

    def _load_slip_image(self):
        self.dispatch_progress('Loading slip')
        self._slip_path = self._book.get_slip(full_path=True)
        assert self._slip_type == self._book.get_slip_type()

    def _print_on_physical_printer(self):
        self.dispatch_progress('Printing slip')
        printer_name = config.get('printer', DEFAULT_PRINTER_NAME)
        conn = cups.Connection()
        conn.printFile(printer_name, self._slip_path, '', {})
        self.dispatch_progress('Slip printed')

    def _send_metrics(self):
        self.dispatch_progress('Sending telemetry')
        payload = {
            'path': self._book.path,
        }
        put_metric('scribe3.book.slip_printed', self._slip_type, payload)
