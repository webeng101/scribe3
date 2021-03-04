from os.path import join, dirname

from kivy.lang import Builder
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout

from ia_scribe.uix.components.poppers.popups import BookMetadataPopup

Builder.load_file(join(dirname(__file__), 'messages.kv'))


class BookMetadataPopupMixin(object):

    _metadata_popup = BookMetadataPopup()

    def __init__(self, *args, **kwargs):
        popup = self._metadata_popup
        popup.fbind('on_open', self._on_metadata_popup_open)
        popup.fbind('on_dismiss', self._on_metadata_popup_dismiss)
        super(BookMetadataPopupMixin, self).__init__(*args, **kwargs)

    def _on_metadata_popup_open(self, popup, *args):
        if not self.scribe_widget:
            raise ValueError('Instance of "ScribeWidget" not set in {}'
                             .format(self))
        popup.md_panel.books_db = self.scribe_widget.books_db
        popup.md_panel.task_scheduler = self.scribe_widget.task_scheduler
        popup.md_panel.backend.fbind('on_metadata_saved',
                                     self._on_metadata_saved)

    def _on_metadata_popup_dismiss(self, popup, *args):
        # popup.md_panel.books_db = None
        popup.md_panel.backend.funbind('on_metadata_saved',
                                       self._on_metadata_saved)

    def _on_metadata_saved(self, md_backend):
        pass


class ScribeMessageGenericContent(BoxLayout):

    text = StringProperty()
    ok_text = StringProperty('OK')
    cancel_text = StringProperty('Cancel')
    trigger_func = ObjectProperty()
    popup = ObjectProperty()
    content = ObjectProperty()

