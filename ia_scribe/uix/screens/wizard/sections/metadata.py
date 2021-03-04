from ia_scribe.uix.screens.settings.metadata_screen import MetadataScreen
from ia_scribe.uix.screens.wizard.sections.base import BaseSection
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.ia_services.c2_registration import ircize_name

from ia_scribe.config.config import Scribe3Configuration
config = Scribe3Configuration()


class MetadataSection(BaseSection, MetadataScreen):

    en_previous_button = False

    def __init__(self, **kwargs):
        super(MetadataSection, self).__init__(**kwargs)

    def before_next(self):
        if self.validate():
            self.save_metadata()
            return True
        else:
            return False

    def on_enter(self):
        super(MetadataSection, self).on_enter()
        self.scanner_name = self._get_scanner_name()
        self.remove_buttons()

    def _get_scanner_name(self):
        login_email_string = config.get('email')
        actual_email = login_email_string.split(';')[0]
        ret = ircize_name(actual_email)
        return ret
