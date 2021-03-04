from ia_scribe.uix.actions.book_task import GreenRedBookTaskSchedulerPopupMixin
from ia_scribe.uix.components.poppers.popups import QuestionPopup, ThreeOptionsQuestionPopup, InfoPopup
from ia_scribe.uix.actions.error import ShowErrorAction
from ia_scribe.book.scandata import PT_FOLDOUT


class UploadBookWrapper(object):
    action_class = None
    concrete_popup = None
    kwargs = []
    book = None

    def __init__(self, **kwargs):
        self.book = kwargs['book']
        self.kwargs = kwargs

    def display(self):
        self.select_action()
        self.instantiate_popup()

    def select_action(self):
        ret, msg = self.book.has_full_image_stack()
        if not ret:
            self.action_class = ShowErrorAction
            self.kwargs['message'] = ('{}\n\nYou must reopen this book and reshoot '
                                      'the missing image(s) before uploading!'
                                      .format(msg))
            return

        if self.book.scandata.has_leafs(PT_FOLDOUT) and \
                not self.book.has_foldout_target_selected():
            self.action_class = UploadBookWithFoldoutsActionMixin
        else:
            self.action_class = UploadBookActionMixin

    def instantiate_popup(self):
        self.concrete_popup = self.action_class(**self.kwargs)
        self.concrete_popup.display()

class UploadBookActionMixin(GreenRedBookTaskSchedulerPopupMixin):
    def __init__(self, **kwargs):
        self.show_send_to_station = kwargs.pop('show_send_to_station', None)
        super(UploadBookActionMixin, self).__init__(**kwargs)
        self.message = ('Are you sure you want to [b]upload[/b] this item?\n\n'
                        'Once an upload is queued, '
                        'it [b]cannot[/b] be canceled.')
        self.popup_cls = QuestionPopup
        self.popup_args = {'title': 'Upload book?',
                           'extra': self.extra_args }
        self.book_command = 'do_queue_processing'


class UploadBookWithFoldoutsActionMixin(GreenRedBookTaskSchedulerPopupMixin):
    def __init__(self, **kwargs):
        self.show_send_to_station = kwargs.pop('show_send_to_station', None)
        super(UploadBookWithFoldoutsActionMixin, self).__init__(**kwargs)
        self.message = ('This item contains a [b]foldout assertion[/b] and\n'
                        'should be sent to a Foldout Scribe for foldout capture.\n\n'
                        'Are you sure you want to upload this item to Republisher?')
        self.popup_cls = ThreeOptionsQuestionPopup
        self.popup_args = {'title': 'Foldout Assertion Detected',
                           'text_else': 'No, send to\nFoldout station',
                           'extra': self.extra_args}
        self.book_command = 'do_queue_processing'


    def on_submit(self, popup, option, *args):
        if option == popup.OPTION_ELSE:
            self.show_send_to_station()
        else:
            super(UploadBookWithFoldoutsActionMixin, self).on_submit(popup, option, *args)


class RetryUploadBookActionMixin(GreenRedBookTaskSchedulerPopupMixin):
    def __init__(self, **kwargs):
        super(RetryUploadBookActionMixin, self).__init__(**kwargs)
        self.message = 'Are you sure you want to try uploading this book again?' \
                       '\n\nThis book experienced an [b]upload error[/b].\n'
        self.popup_cls = QuestionPopup
        self.popup_args = {'title': 'Try upload again?',
                           'extra': kwargs.get('extra'), }
        self.book_command = 'do_upload_book_retry'


class ForceUploadBookActionMixin(GreenRedBookTaskSchedulerPopupMixin):
    def __init__(self, **kwargs):
        super(ForceUploadBookActionMixin, self).__init__(**kwargs)
        self.message = ('This book encountered an [b]upload error[/b]\n'
                        'and may require manual intervention.\n\n'
                        'Forcing the upload will [b]overwrite[/b] any previously\n'
                        'uploaded [b]images[/b], and cannot be reversed.\n\n'
                        'Are you sure you want to force uploading this book?')
        self.popup_cls = QuestionPopup
        self.popup_args = {'title': 'Force book upload?',
                           'extra': kwargs.get('extra'), }
        self.book_command = ['set_force_upload', 'do_upload_book_retry' ]


class RetryUploadCorrectionsBookActionMixin(GreenRedBookTaskSchedulerPopupMixin):
    def __init__(self, **kwargs):
        super(RetryUploadCorrectionsBookActionMixin, self).__init__(**kwargs)
        self.message = ('Are you sure you want to try uploading '
                     '\nthis corrections book again?')
        self.popup_cls = QuestionPopup
        self.popup_args = {'title': 'Try upload again?',
                           'extra': kwargs.get('extra'), }
        self.book_command = 'do_queue_upload_corrections'


class RetryUploadFoldoutsBookActionMixin(GreenRedBookTaskSchedulerPopupMixin):
    def __init__(self, **kwargs):
        super(RetryUploadFoldoutsBookActionMixin, self).__init__(**kwargs)
        self.message = ('Are you sure you want to try uploading '
                     '\nthis foldouts book again?')
        self.popup_cls = QuestionPopup
        self.popup_args = {'title': 'Try upload again?',
                           'extra': kwargs.get('extra'), }
        self.book_command = 'do_queue_upload_foldouts'


class UploadCorrectionsBookActionMixin(GreenRedBookTaskSchedulerPopupMixin):
    def __init__(self, **kwargs):
        super(UploadCorrectionsBookActionMixin, self).__init__(**kwargs)
        self.message = 'Do you want to upload these [b]corrections[/b] back to RePublisher?'
        self.popup_cls = QuestionPopup
        self.popup_args = {'title': 'Upload corrections?',
                           'extra': kwargs.get('extra'), }
        self.book_command = 'do_queue_upload_corrections'

class UploadFoldoutsBookActionMixin(GreenRedBookTaskSchedulerPopupMixin):
    def __init__(self, **kwargs):
        super(UploadFoldoutsBookActionMixin, self).__init__(**kwargs)
        self.message = 'Do you want to upload these [b]foldouts[/b] back to RePublisher?'
        self.popup_cls = QuestionPopup
        self.popup_args = {'title': 'Upload corrections?',
                           'extra': kwargs.get('extra'), }
        self.book_command = 'do_queue_upload_foldouts'


class UploadAnewBookActionMixin(GreenRedBookTaskSchedulerPopupMixin):
    def __init__(self, **kwargs):
        self.target_name = kwargs.pop('target_name', None)
        self.target_status = kwargs.pop('target_status', None)
        self.title = 'Upload {} book again'.format(self.target_name)
        self.message = ("Are you sure you want to [b]retry uploading[/b]"
                     "\nthis book again?\n\nThis is a [b]{}[/b] item."
                     "\n\nOnce an upload is queued "
                     "\nit [b]cannot[/b] be canceled.".format(self.target_name))
        self.popup_args = {'title': 'Try again {}'.format(self.target_status.name),
                           'extra': kwargs.pop('extra', None),
                           'target_status': self.target_status
                           }
        super(UploadAnewBookActionMixin, self).__init__(**kwargs)
        self.popup_cls = QuestionPopup
        self.book_command = 'do_upload_book_anew'