import json

import ia_scribe.tasks.book_tasks.upload
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.tasks.task_base import TaskBase
from ia_scribe.tasks.book_tasks.upload import _prepare_metadata
from ia_scribe.ia_services.btserver import get_ia_session
from ia_scribe.ia_services.iabdash import push_event
from ia_scribe.ia_services.ingestion_adapters import put_metric
from ia_scribe.utils import get_string_value_if_list
from ia_scribe.tasks.book_tasks.identifier import make_identifier

config = Scribe3Configuration()

class MakeIdentifierTask(TaskBase):

    def __init__(self, **kwargs):
        self.book = kwargs['book']
        super(MakeIdentifierTask, self).__init__(logger=kwargs['book'].logger, **kwargs)

    def create_pipeline(self):
        return [self._make_identifier,
                self._change_book_state,
                self._write_identifier_file,
                ]

    def _make_identifier(self):
        self.dispatch_progress('Loading book')

        if self.book.has_minimal_metadata(exclude_catalog = True):
            self.make_identifier_from_metadata()
        else:
            self._make_identifier_nomarc()


    def make_identifier_from_metadata(self):
        self.dispatch_progress('Creating new identifier from metadata')
        self.identifier = result = make_identifier(
            title=self.book.metadata.get('title', None) or 'unset',
            volume=self.book.metadata.get('volume', None) or '00',
            creator=get_string_value_if_list(self.book.metadata, 'creator') or 'unset'
        )
        return result

    def _make_identifier_nomarc(self):
        if self.book.metadata.get('scribe3_search_catalog'):
            self.dispatch_progress('Creating new identifier from search catalog')
            identifier_base = '{catalog}_{search_id}' \
                .format(catalog=self.book.metadata.get('scribe3_search_catalog'),
                        search_id=self.book.metadata.get('scribe3_search_id'))
        else:
            identifier_base = self.make_identifier_from_metadata()

        self.volume = self.book.metadata.get('volume')
        if self.volume and self.volume != '0':
            self.dispatch_progress('Mangling with volume information')
            identifier_base += '_{}'.format(self.volume)

        num_attempts = 10
        for i in range(num_attempts):
            self.dispatch_progress('Negotiating with Archive.org [{}/{}]'.format(i, num_attempts))
            if i == 0:
                random_str = ''
            else:
                random_str = '_' + ia_scribe.tasks.book_tasks.upload.random_string()

            identifier = ('{base}{rand}'
                          .format(base=identifier_base, rand=random_str))
            if ia_scribe.tasks.book_tasks.upload.id_available(identifier):
                self.dispatch_progress('Created identifier {}'.format(identifier))
                self.identifier = identifier
                return identifier
        raise Exception('Failed to generate a valid identifier after {} attempts'.format(num_attempts))

    def _write_identifier_file(self):
        self.dispatch_progress('Writing identifier file')
        self.book.set_identifier(self.identifier)

    def _change_book_state(self):
        if self.book.status == 'identifier_assigned':
            self.logger.info('_change_book_state: Nothing to do, '
                        '{} is already in status identifier_assigned'.format(self.book))
            return
        self.dispatch_progress('Changing book state')
        if self.book.can('do_create_identifier'):
            self.book.do_create_identifier()

class CreateModernItemTask(TaskBase):

    def __init__(self, **kwargs):
        super(CreateModernItemTask, self).__init__(logger=kwargs['book'].logger, **kwargs)
        self.book = kwargs['book']
        self.skip_metadata = False
        self.force = kwargs['force']
        self.user_input = None
        self.ia_item = None
        self.identifier = None
        self.user_intends_to_just_reprint = False

    def create_pipeline(self):
        return [
            self._load_identifier,
            self._load_item,
            self._test_user_intention,
            self._test_repub_state,
            self._reserve_identifier,
            self._push_metadata,
            self._change_book_state,
        ]

    def _load_identifier(self):
        self.dispatch_progress('Loading identifier from disk')
        identifier = self.book.identifier
        if not identifier:
            raise Exception('No identifier provided')
        self.identifier = identifier

    def _load_item(self):
        self.dispatch_progress('Asking Archive.org for {}'.format(self.identifier))
        self.ia_item = get_ia_session().get_item(self.identifier)

    def _test_user_intention(self):
        if self.ia_item.exists:
            self.dispatch_progress('{} exists on Archive.org'.format(self.identifier))
            if not self.user_input:
                self.pause()
                self.dispatch_progress('Step %s' % self._current_index,
                                       task=self,
                                       input_needed=True, title='Item already exists',
                                       popup_body_message='This item already exists. Do you want to just re-print the slip,'
                                                          'or are you trying to actually update it?\n'
                                                          'Press Cancel if you are not sure.',
                                       text_yes = 'Reprint',
                                       text_no = 'Update',)
                self._stay_on_current_step = True
            else:
                self.dispatch_progress('Step %s: User input: %s'
                                       % (self._current_index, self.user_input))
                self._stay_on_current_step = False
                if self.user_input == 'yes':
                    self.user_intends_to_just_reprint = True
                    self.logger.info('User says they just want to re-print the slip for {}'.format(self.identifier))
                elif self.user_input == 'no':
                    self.user_intends_to_just_reprint = False
                    self.logger.info('User say they want to make a new slip for {}'.format(self.identifier))
                elif self.user_input == 'else':
                    raise Exception('Ok, the Print Slip task was canceled.')
                self.user_input = None

        else:
            self.dispatch_progress('{} does not exist on Archive.org'.format(self.identifier))
            self.skip_metadata = True

    def _test_repub_state(self):
        self.dispatch_progress('Testing repub_state for {}'.format(self.identifier))
        if not self.ia_item.exists:
            self.dispatch_progress('Item does not exist: skipping.')
            return
        if self.user_intends_to_just_reprint:
            self.dispatch_progress('Item exist but user does not want to overwrite.')
            return

        self.dispatch_progress('Verifying repub_state for {}'.format(self.identifier))
        repub_state = self.ia_item.metadata.get('repub_state')

        self.dispatch_progress('Read {} from MDAPI for {}'.format(repub_state,
                                                                  self.identifier))

        if repub_state is not None:
            if int(repub_state) > 0:
                raise Exception('This item has already been uploaded to.\n'
                                'Uploading a slip is not allowed.\n'
                                'Contact a supervisor to resolve.')

            elif int(repub_state) == -2:
                if not self.user_input:
                    self.pause()
                    # Flag progress report that user input is need for task to
                    # continue. Keyword `input_needed` is arbitrary
                    self.dispatch_progress('Step %s' % self._current_index,
                                           task=self,
                                           input_needed=True, title='Overwrite item?',
                                           popup_body_message='This item already exists and has -2 repub_state.'
                                                              'Are you sure you want to upload a new slip to it?',
                                           )
                    self._stay_on_current_step = True
                else:
                    self.dispatch_progress('Step %s: User input: %s'
                                           % (self._current_index, self.user_input))
                    self._stay_on_current_step = False
                    if self.user_input == 'yes':
                        self.user_input = None
                        self.logger.info('User elected to overwrite the slip in {}'.format(self.identifier))
                    elif self.user_input == 'no':
                        raise Exception('You have elected not to overwrite this item.'
                                        '\nTask terminated.')
                    elif self.user_input == 'else':
                        raise Exception('Task #canceled by user.')

    def _reserve_identifier(self):
        if self.user_intends_to_just_reprint:
            return
        self.dispatch_progress('Uploading slip to {}'.format(self.identifier))
        encoded_md = _prepare_metadata(self.book, self.ia_item, self.logger, override=self.skip_metadata)
        encoded_md['repub_state'] = -2
        if config.is_true('set_noindex'):
            encoded_md['noindex'] = 'true'
        self.logger.info('Metadata -> {}'.format(encoded_md))

        target_file_name = '{}_{}'.format(self.identifier, 'slip.png')
        self.dispatch_progress('Uploading {} to {}'.format(target_file_name, self.identifier))
        self._slip_filename = self.book.get_slip(full_path = True)
        response = self.ia_item.upload({target_file_name: self._slip_filename},
                                  metadata=encoded_md,
                                  retries=10,
                                  retries_sleep=1,
                                  queue_derive=False,
                                  verify=True, )
        assert len(response) > 0
        assert response[0].status_code == 200, "Invalid {} response from IA".format(response[0].status_code)
        self.dispatch_progress('{} reserved'.format(self.identifier))

    def _push_metadata(self):
        if not self.ia_item.exists:
            return

        if self.user_intends_to_just_reprint:
            return

        if self.skip_metadata is True:
            self.logger.info('Skipping metadata push new item (as it was pushed already)')
            return

        self.dispatch_progress('Pushing metadata to {}'.format(self.identifier))

        encoded_md = _prepare_metadata(self.book, self.ia_item, self.logger, override=True)
        encoded_md['repub_state'] = -2
        if config.is_true('set_noindex'):
            encoded_md['noindex'] = 'true'
        self.logger.info('Metadata -> {}'.format(encoded_md))
        response_md = self.ia_item.modify_metadata(encoded_md)

        assert response_md is not None, "Response from MDAPI is empty"

        # Jim confirmed that MDAPI never returns 400 without
        # a json blob, so we can treat them the same (since it will also return 400 for no-ops)
        assert response_md.status_code in [200, 400], "Invalid {} response from MDAPI: {}".format(response_md.status_code,
                                                                                           response_md.text)
        assert response_md.text is not None, "Response from MDAPI  is incorrect"
        self.logger.info('Response from MDAPI -> {}'.format(response_md.text))

        # if the 400 is out of nginx, this will fail because we'll get straight up html
        response_md_json = json.loads(response_md.text)

        if 'error' in response_md_json:
            if response_md_json['error'] == 'no changes to _meta.xml':
                pass
            else:
                raise Exception('Metadata API courteously\n'
                            'tucked an error into a valid response.\n'
                            'What seems to have gone wrong is\n\n{}'
                            .format(str(response_md_json['error'])))
        self.dispatch_progress('Metadata pushed to {}'.format(self.identifier))

    def _change_book_state(self):
        if self.book.status == 'identifier_assigned':
            self.logger.info('_change_book_state: Nothing to do, '
                        '{} is already in status identifier_assigned'.format(self.book))
            return

        if self.book.can('do_create_identifier'):
            self.book.do_create_identifier()


class UpdateItemMetadataTask(TaskBase):

    def __init__(self, **kwargs):
        super(UpdateItemMetadataTask, self).__init__(logger=kwargs['book'].logger, **kwargs)
        self.book = kwargs['book']
        self.force = kwargs['force']
        self.user_input = None

    def create_pipeline(self):
        return [
            self._load_identifier,
            self._load_item,
            self._test_user_intention,
            self._test_repub_state,
            self._reserve_identifier,
            self._push_metadata,
        ]
