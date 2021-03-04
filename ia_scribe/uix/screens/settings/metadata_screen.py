import copy
from os.path import join, dirname

from kivy.lang import Builder
from kivy.logger import Logger
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, ListProperty

from ia_scribe import scribe_globals
from ia_scribe.book.metadata import get_metadata, set_metadata
from ia_scribe.uix.components.form.form_inputs import MetadataTextInput, EmailTextInput, ScannerTextInput
from ia_scribe.ia_services.rcs import RCS

Builder.load_file(join(dirname(__file__), 'metadata_screen.kv'))


class MetadataScreen(Screen):

    scanner_name = StringProperty('')
    centers = ListProperty()


    def __init__(self, **kwargs):
        super(MetadataScreen, self).__init__(**kwargs)
        self.rcs = RCS()

    def on_enter(self):
        # Get scan center metadata.xml from disk
        config = get_metadata(scribe_globals.SCANCENTER_METADATA_DIR)
        # Get all widgets
        widgets = [x for x in self.ids['_metadata'].children
                   if isinstance(x, MetadataTextInput)]
        # Populate
        for widget in widgets:
            val = config.get(widget.metadata_key)
            self.set_val(widget, val)

    def save_metadata(self):
        # Get the metadata from the default location
        # TODO: Try catch, dependency on figuring out what the best course of
        # action would be
        config = get_metadata(scribe_globals.SCANCENTER_METADATA_DIR)
        config.pop('collection', None)
        # Make a copy of it
        new_config = copy.deepcopy(config)
        # For each of them, get the value in the textbox and assign it to the
        # new copy of the dict
        for widget in self.ids['_metadata'].children:
            if isinstance(widget, (MetadataTextInput, EmailTextInput, ScannerTextInput)):
                val = self.get_val(widget)
                new_config[widget.metadata_key] = val
        Logger.debug('MetadataScreen: Read from widget: {0}'
                     .format(new_config))
        # If the two dicts are different, set the new one as default
        if config != new_config:
            set_metadata(new_config, scribe_globals.SCANCENTER_METADATA_DIR)

    @staticmethod
    def get_scribe_version():
        return '{v}'.format(v=scribe_globals.release_version)

    def remove_buttons(self):
        for _id in ['btn_edit', 'lb_edit', 'btn_save', 'lb_save']:
            if _id in self.ids:
                self.ids['_metadata'].remove_widget(self.ids[_id])

    def validate(self):
        '''Walk through all metadata input widgets and validate values.'''
        self.centers = self.rcs.remote_get_aggregate('center')
        if len(self.centers) == 0:
            return False
        is_valid = True
        for widget in self.ids['_metadata'].children:
            if isinstance(widget, (MetadataTextInput, EmailTextInput, ScannerTextInput)):
                if len(widget.text.strip()) == 0:
                    is_valid = False
                    widget.mark_as_error()
                elif widget.metadata_key == 'scanningcenter':
                    if not self.get_val(widget) in self.centers:
                        is_valid = False
                        widget.mark_as_error()
                elif widget.metadata_key == 'scanner' and not widget.is_valid:
                    is_valid = False
                    widget.mark_as_error()
        return is_valid

