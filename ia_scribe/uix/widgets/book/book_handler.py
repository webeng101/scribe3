import webbrowser
from os.path import exists

from kivy.logger import Logger

from ia_scribe.uix.actions.book_task import GreenRedBookTaskSchedulerPopupMixin
from ia_scribe.uix.actions.info import ShowInfoActionPopupMixin, ShowPathAction
from ia_scribe.uix.actions.send_to_station import SendToStationActionMixin
from ia_scribe.uix.actions.error import ShowErrorAction
from ia_scribe.uix.actions.book_reset import ResetBookActionMixin
from ia_scribe.uix.actions.book_delete import DeleteBookActionMixin
from ia_scribe.uix.actions.book_upload import (UploadBookWrapper,
                                               ForceUploadBookActionMixin,
                                               UploadAnewBookActionMixin,
                                               UploadCorrectionsBookActionMixin,
                                               UploadFoldoutsBookActionMixin,
                                               RetryUploadBookActionMixin,
                                               RetryUploadFoldoutsBookActionMixin,
                                               RetryUploadCorrectionsBookActionMixin)
from ia_scribe.uix.widgets.export.book_export import BookExport
from ia_scribe.uix.components.messages.messages import BookMetadataPopupMixin
from ia_scribe.uix.components.poppers.popups import ProgressPopup
from ia_scribe.uix.widgets.book.book_menu_popup import BookMenuPopup
from ia_scribe.book.upload_status import UploadStatus, status_human_readable
from ia_scribe.utils import get_string_value_if_list
from ia_scribe.tasks.ui_handlers.deferred_metadata_task_ui_handler import DeferredMetadataViaWonderfetchUIHandler
from ia_scribe.tasks.ui_handlers.generic import GenericUIHandler
from ia_scribe.tasks.book import MoveAlongBookTask, BookTask, BookMultiTask
from ia_scribe.book.book import get_upload_target


class BookHandler(BookMetadataPopupMixin):

    def __init__(self, upload_widget):
        super(BookHandler, self).__init__()
        self._book_export = None
        self.upload_widget = upload_widget
        self.scribe_widget = upload_widget.scribe_widget
        self.screen_manager = upload_widget.screen_manager
        self.book_menu_popup = popup = BookMenuPopup()
        self.task_scheduler = upload_widget.task_scheduler
        self.progress_popup = ProgressPopup()
        popup.fbind('on_submit', self._on_book_option_submit)
        self._handlers = {
            'cancel': self.cancel,
            'open': self.open,
            'edit_metadata': self.edit_metadata,
            'retry_metadata': self.retry_metadata,
            'delete': self.delete,
            'upload': self.upload,
            'export': self.export,
            'move_to_scribing': self.move_to_scribing,
            'retry_upload': self.retry_upload,
            'force_upload': self.force_upload,
            'retry_compression': self.retry_compression,
            'retry_preimage': self.retry_preimage,
            'package_uncompressed_imgstack':
                self.package_uncompressed_imgstack,
            'open_browser': self.open_browser,
            'open_reshooting_index': self.open_reshooting_index,
            'open_foldouts': self.open_foldouts,
            'start_foldouts': self.start_foldouts,
            'start_corrections': self.start_corrections,
            'upload_corrections': self.upload_corrections,
            'upload_foldouts': self.upload_foldouts,
            'retry_upload_corrections': self.retry_upload_corrections,
            'retry_upload_foldouts': self.retry_upload_foldouts,
            'upload_done_book_anew': self.upload_done_book_anew,
            'show_plan': self.show_plan,
            'show_next_states': self.show_next_states,
            'do_action': self.do_action,
            'move_along': self.move_along,
            'skip_blur_detection': self.skip_blur_detection,
            'retry_blur_detection': self.retry_blur_detection,
            'retry_packaging': self.retry_packaging,
            'delete_staged': self.delete_staged,
            'undelete_staged': self.undelete_staged,
            'delete_anyway': self.delete_anyway,
            'reset_and_delete': self.reset_and_delete,
        }

    '''
    Form methods
    '''

    def on_select(self, library_view, book):
        Logger.info('BookHandler: Selected book: {}'
                    .format(self.book_to_string(book)))
        self.book_menu_popup.init_from_data(book)
        self.book_menu_popup.open()

    def _on_book_option_submit(self, popup, option):
        if type(option) == tuple:
            handler = self._handlers.get(option[0], None)
            handler(popup.book, option[1])
        else:
            handler = self._handlers.get(option, None)
            handler(popup.book) if handler else self.cancel(popup.book)

    '''
    Buttons that do not require user interaction to do the thing
    they are meant to do (e.g. open capture screen)
    '''

    def cancel(self, book=None):
        self.book_menu_popup.dismiss()

    def move_along(self, book, **kwargs):
        book_obj = self.get_book_object(book)
        task_handler = GenericUIHandler(
            task_type=MoveAlongBookTask,
            book=book_obj)
        self.task_scheduler.schedule(task_handler.task)

    def open(self, book):
        if self.screen_manager.current == 'capture_screen':
            self.action = ShowErrorAction(
                message='Another book is currently open for scanning.\n'
                        'Please close the current book before opening a new one.',
                on_popup_dismiss=self._action_no_op_callback)
            self.action.display()
            return
        capture_screen = self.scribe_widget.ids._capture_screen
        capture_screen.book_dir = book['path']
        target_screen = 'capture_screen'
        self.screen_manager.transition.direction = 'left'
        self.screen_manager.current = target_screen
        self.book_menu_popup.dismiss()

    def open_reshooting_index(self, book):
        self.book_menu_popup.dismiss()
        self.screen_manager.transition.direction = 'left'
        rescribe_screen = self.screen_manager.get_screen('rescribe_screen')
        rescribe_screen.book = book
        rescribe_screen.scribe_widget = self.scribe_widget
        rescribe_screen.screen_manager = self.screen_manager
        self.screen_manager.current = 'rescribe_screen'

    def open_foldouts(self, book):
        self.open(book)

    def open_browser(self, book):
        # self.book_menu_popup.dismiss()
        url = ('https://archive.org/details/{i}'
               .format(i=book.get('identifier', '')))
        webbrowser.open(url)

    def edit_metadata(self, book):
        path = book['path']
        if path and exists(path):
            self._metadata_popup.book_path = path
            self._metadata_popup.open()
        else:
            Logger.warn('BookHandler: Tried to open book metadata popup '
                        'with path which does not exist')

    def retry_metadata(self, book):
        book_obj = self.get_book_object(book)
        task_handler = DeferredMetadataViaWonderfetchUIHandler(book=book_obj)
        self.task_scheduler.schedule(task_handler.task)

    def export(self, book):
        # self.book_menu_popup.dismiss()
        self._book_export = export = BookExport(book['path'])
        export.fbind('on_finish', self._on_export_finish)
        export.start()

    def _on_export_finish(self, *args):
        self._book_export = None

    def show_plan(self, b):
        book = self.get_book_object(b)
        message = '[b]In order to upload, we need to go through these ' \
                     'stages:[/b]\n'
        self.action = ShowPathAction(book=book,
                                     message=message,
                                     on_popup_dismiss=self._action_no_op_callback)
        self.action.display()

    def show_next_states(self, book):
        book = self.get_book_object(book)
        message = 'Seeing as it is currently in\n[b]{}[/b] status,\n' \
                  '[b]{}[/b] can move to the following states next:\n\n'.format(book.get_status(human_readable=True),
                                                            book.name_human_readable())
        next_states = book.get_available_next_states(human_readable=True)
        for state in next_states:
            state_string = '[b]{}[/b]\n'.format(state)
            message += state_string
        self.action = ShowInfoActionPopupMixin(message=message,
                                               on_popup_dismiss=self._action_no_op_callback)
        self.action.display()

    '''
    Interactions: asking the user before doing something
    '''

    def upload(self, book):
        book_object = self.get_book_object(book)
        self.action = UploadBookWrapper(book=book_object,
                                        task_scheduler=self.scribe_widget.task_scheduler,
                                        show_send_to_station=self.show_send_to_station_popup,
                                        done_action_callback = self._action_no_op_callback
                                        )
        self.action.display()

    def show_send_to_station_popup(self, *args):

        '''
        msg = 'This feature is not yet supported from here. ' \
              'Please open the book and queue upload from inside CaptureScreen ' \
              'in order to send to station.'
        self.action = ShowErrorAction(message=msg,
                                      on_popup_dismiss=self._action_no_op_callback)
        self.action.display()
        return False
        '''
        book_object = self.action.book
        self.action = SendToStationActionMixin(
            book=book_object,
            on_popup_dismiss=self._action_no_op_callback
        )
        self.action.display()

    def delete(self, book):
        self.book_menu_popup.dismiss()
        book_object = self.get_book_object(book)
        if book_object.is_preloaded():
            self.action = DeleteBookActionMixin(
                book=book_object,
                task_scheduler=self.task_scheduler,
                done_action_callback=self._action_no_op_callback
            )
        else :
            self.action = ResetBookActionMixin(book=book_object,
                                           task_scheduler=self.task_scheduler,
                                           done_task_callback=self.book_reset_callback
                                           )
        self.action.display()

    def retry_upload(self, book):
        self.action = RetryUploadBookActionMixin(
            book=self.get_book_object(book),
            task_scheduler=self.task_scheduler,
            done_action_callback=self._action_no_op_callback
        )
        self.action.display()

    def force_upload(self, book):
        self.action = ForceUploadBookActionMixin(
            book=self.get_book_object(book),
            task_scheduler=self.task_scheduler,
            done_action_callback=self._action_no_op_callback
        )
        self.action.display()

    def upload_corrections(self, book):
        book_object = self.get_book_object(book)
        self.action = UploadCorrectionsBookActionMixin(book=book_object,
                                                       task_scheduler=self.task_scheduler,
                                                       done_task_callback=self.book_reset_callback
                                                       )
        self.action.display()

    def upload_foldouts(self, book):
        book_object = self.get_book_object(book)
        self.action = UploadFoldoutsBookActionMixin(book=book_object,
                                                    task_scheduler=self.task_scheduler,
                                                    done_task_callback=self.book_reset_callback
                                                    )
        self.action.display()

    def retry_upload_corrections(self, book):
        book_object = self.get_book_object(book)
        self.action = RetryUploadCorrectionsBookActionMixin(book=book_object,
                                                            task_scheduler=self.task_scheduler,
                                                            done_task_callback=self.book_reset_callback
                                                            )
        self.action.display()

    def retry_upload_foldouts(self, book):
        book_object = self.get_book_object(book)
        self.action = RetryUploadFoldoutsBookActionMixin(book=book_object,
                                                         task_scheduler=self.task_scheduler,
                                                         done_task_callback=self.book_reset_callback
                                                         )
        self.action.display()

    def reset_and_delete(self, book):
        book_object = self.get_book_object(book)
        self.action = ResetBookActionMixin(book=book_object,
                                           task_scheduler=self.task_scheduler,
                                           done_task_callback=self.book_reset_callback
                                           )
        self.action.display()

    def upload_done_book_anew(self, book):
        target_status, target_name = get_upload_target(book)
        if not target_status:
            self.action = ShowErrorAction(message='Book error'\
                                                   'Could not tell if book is a\nfoldouts or '\
                                                   'corrections item.\nPlease contact an admin.',
                                          on_popup_dismiss=self._action_no_op_callback)
            self.action.display()
            return

        book_object = self.get_book_object(book)
        self.action = UploadAnewBookActionMixin(book=book_object,
                                                task_scheduler=self.task_scheduler,
                                                done_task_callback=self.book_reset_callback,
                                                target_name=target_name,
                                                target_status=target_status,
                                                )
        self.action.display()

    '''
    Direct actions: run the book state transition as soon as the button is pushed
    '''

    def start_corrections(self, book_dict):
        book = self.get_book_object(book_dict)
        task_handler = GenericUIHandler(
                        task_type=BookTask,
                        book=book,
                        command='do_start_corrections')
        self.task_scheduler.schedule(task_handler.task)

    '''
     Indirect actions: run the book state transition after a confirmation button is pressed
    '''

    def do_action(self, book, action):
        self.run_book_function_as_task_by_uuid(book, [action])

    def skip_blur_detection(self, book):
        self.do_action(book, 'do_ignore_blur_detection')

    def retry_blur_detection(self, book):
        self.do_action(book, 'do_retry_blur_detection')

    def retry_packaging(self, book):
        self.do_action(book, 'do_retry_packaging')

    def delete_staged(self, book):
        self.do_action(book, 'do_delete_staged')

    def undelete_staged(self, book):
        self.do_action(book, 'do_undelete_staged')

    def delete_anyway(self, book):
        self.do_action(book, 'do_delete_anyway')

    def move_to_scribing(self, book):
        self.do_action(book, 'do_move_back_to_scribing')

    def package_uncompressed_imgstack(self, book):
        self.do_action(book, 'do_create_preimage_zip')

    def retry_compression(self, book):
        self.do_action(book, 'do_retry_image_stack')

    def retry_preimage(self, book):
        self.do_action(book, 'do_retry_preimage_zip')

    def start_foldouts(self, book):
        self.run_book_function_as_task_by_uuid_without_confirm(book, ['do_start_foldouts'])

    '''
    Convenience methods
    '''
    def run_book_function_as_task_by_uuid(self, book_uuid, commands):
        book = self.get_book_object(book_uuid)
        self.action = GreenRedBookTaskSchedulerPopupMixin(
            message='Would you like to run {} on {}?'.format(commands, book.name_human_readable()),
            title='Run {}?'.format(commands),
            book=book,
            book_command=commands,
            task_scheduler=self.task_scheduler
        )
        self.action.display()

    def run_book_function_as_task_by_uuid_without_confirm(self, book_uuid, commands):
        book = self.get_book_object(book_uuid)
        task_args = {}
        task_config = {
            'task_type': BookTask,
            'book': book,
            'args': task_args,
        }
        # Support lists of tasks by dispatching a BookMultiTask
        if type(commands) is list:
            task_config['task_type'] = BookMultiTask
            task_config['scheduling_callback'] = self.task_scheduler.schedule
        task_config['command'] = commands
        self.task_scheduler.schedule(BookMultiTask(**task_config))

    def get_book_object(self, bk):
        if type(bk) == dict:
            selector = bk['uuid']
        else:
            selector = bk
        library = self.scribe_widget.books_db
        book_object = library.get_item(selector)
        return book_object

    def get_book_status(self, book):
        try:
            status = UploadStatus(book.get('status')).name
            return status_human_readable.get(status, status)
        except ValueError:
            return 'Unknown status'

    def book_reset_callback(self, book, task, *args):
        self.action = None
        if not task.error:
            self.cancel()

    # This is the callback that interactions use
    def _action_no_op_callback(self, *args, **kwargs):
        self.action = None

    def book_to_string(self, book):
        none_str = 'None'
        if book is None:
            return none_str
        identifier = book.get('identifier', None) or none_str
        creator = (get_string_value_if_list(book, 'creator')
                   or get_string_value_if_list(book, 'author')
                   or none_str)
        title = book.get('title', None) or none_str
        return (
            '<identifier="{}", status="{}", title="{}", creator="{}">'
            .format(identifier, self.get_book_status(book), title, creator)
        )
