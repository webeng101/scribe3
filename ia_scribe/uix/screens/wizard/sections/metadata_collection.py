from kivy.logger import Logger

from ia_scribe import scribe_globals
#from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.book.metadata import get_metadata
from ia_scribe.ia_services.iabdash import push_event
from ia_scribe.ia_services.tts import TTSServices
from ia_scribe.uix.screens.settings.metadata_collection_screen import MetadataCollectionsScreen
from ia_scribe.uix.screens.wizard.sections.base import BaseSection
from ia_scribe.utils import restart_app
from ia_scribe.uix.actions.error import ShowErrorAction


class MetadataCollectionSection(BaseSection, MetadataCollectionsScreen):

    def __init__(self, **kwargs):
        super(MetadataCollectionSection, self).__init__(**kwargs)

    def on_enter(self):
        super(MetadataCollectionSection, self).on_enter()

    def restart_app(self, *args, **kwargs):
        restart_app()

    def before_next(self):
        self.message = self.bt_server_register()
        if len(self.message) > 0:
            self.action = ShowErrorAction(
                    message = self.message,
                    on_popup_dismiss=self.restart_app)
            self.action.display()

    @staticmethod
    def bt_server_register():
        message = ''
        #config = Scribe3Configuration()
        Logger.info('bt_server_register: Registering scribe')
        try:
            dd = dict((k, v) for k, v in
                      get_metadata(scribe_globals.CONFIG_DIR).items() if v)
            dd['books'] = '[]'
            tts = TTSServices(dd)
            success, tts_id = tts.register_tts(tts_id=dd['scanner'],
                                               metadata=dd)
            if success:
                #config.set('identifier', str(tts_id))
                push_event('tts-register', dd, 'tts', tts_id)
                Logger.info('bt_server_register: Registered scribe: {}'
                            .format(tts_id))

            else:
                message =  'bt_server_register: Could not register this '\
                                'scribe with Archive.org or scribe already '\
                                'registered'
                Logger.info(message)
        except Exception:
            message =  'bt_server_register: Failed to register'
            Logger.exception(message)
        return message
        