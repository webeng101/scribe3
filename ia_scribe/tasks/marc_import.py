import base64
from os.path import join

from ia_scribe.book.metadata import set_metadata
from ia_scribe.tasks.book_tasks.identifier import make_identifier
from ia_scribe.tasks.task_base import TaskBase
from ia_scribe.utils import get_string_value_if_list


class MetadataViaMARCTask(TaskBase):

    def __init__(self, **kwargs):
        super(MetadataViaMARCTask, self).__init__(**kwargs)
        self._marc_data = kwargs['data']
        self._query = kwargs['query']
        self.book = kwargs['book']

    def create_pipeline(self):
        return [
            self._write_marc_XML,
            self._write_marc_bin,
            self._write_dublin_core,
            self._extract_metadata,
            self._add_query_information,
            self._write_metdata,
            self._create_identifier,
        ]

    def _write_marc_XML(self):
        if 'xml' in self._marc_data:
            self.dispatch_progress('Writing MARCXML')
            with open(join(self.book.path, 'marc.xml'), 'w+') as fd:
                fd.write(self._marc_data['xml'])

    def _write_marc_bin(self):
        if 'binary_base_64_encoded' in self._marc_data:
            self.dispatch_progress('Writing MARC binary')
            with open(join(self.book.path, 'marc.bin'), 'wb+') as fd:
                marcbin = base64.b64decode(self._marc_data['binary_base_64_encoded'])
                fd.write(marcbin)

    def _write_dublin_core(self):
        if 'dublin_core' in self._marc_data['dc_meta']:
            self.dispatch_progress('Writing Dublin Core')
            with open(join(self.book.path, 'dc.xml'), 'w+') as fd:
                fd.write(self._marc_data['dc_meta']['dublin_core'])

    def _extract_metadata(self):
        self.dispatch_progress('Converting metadata')
        self.metadata = md = self._marc_data['dc_meta']['metadata']
        for key in list(md.keys()):
            if self.metadata[key] in ['', None]:
                self.metadata.pop(key)
        for key, value in self.metadata.items():
            if type(value) is dict:
                dict_as_list = list(value.values())
                self.metadata[key] = dict_as_list

    def _add_query_information(self):
        self.dispatch_progress('Adding query information to metadata')

    def _write_metdata(self):
        self.dispatch_progress('Saving metadata')
        set_metadata(self.metadata, self.book.path)

    def _create_identifier(self):
        self.dispatch_progress('Creating identifier')
        self.identifier = identifier = make_identifier(
            title=self.metadata.get('title', None) or 'unset',
            volume=self.metadata.get('volume', None) or '00',
            creator=get_string_value_if_list(self.metadata, 'creator') or 'unset'
        )
        self.dispatch_progress('Setting identifier to {}'.format(identifier))
        with open(join(self.book.path, 'identifier.txt'), 'w') as fd:
            fd.write(identifier)