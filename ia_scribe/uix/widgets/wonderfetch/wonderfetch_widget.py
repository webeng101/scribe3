import glob, re
from os.path import join, dirname, basename
from functools import partial

from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import (
    ObjectProperty,
    StringProperty,
    ListProperty,
    NumericProperty,
    DictProperty,
)
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import SlideTransition

from ia_scribe import scribe_globals
from ia_scribe.config.config import Scribe3Configuration

from ia_scribe.uix.components.form.form_inputs import MetadataTextInput
from ia_scribe.uix.components.simple_list.simple_list import SimpleList
from ia_scribe.uix.components.poppers.popups import NumberPopup
from ia_scribe.uix.components.buttons.buttons import ColorButton
from ia_scribe.uix.widgets.wonderfetch.wonderfetch_backend import build_list, get_api_result, parse_response

Builder.load_file(join(dirname(__file__), 'wonderfetch_widget.kv'))

config = Scribe3Configuration()

CATALOGS = tuple(config.get('catalogs', scribe_globals.CATALOGS).keys())
DEFAULT_CATALOG = config.get('default_catalog', scribe_globals.DEFAULT_CATALOG)


class WonderfetchDialog(Popup):

    EVENT_SCAN_BOOK = 'on_scan_book'
    EVENT_CANNOT_SCAN_BOOK = 'on_cannot_scan_book'
    EVENT_SCAN_EXISTING_BOOK = 'on_scan_existing_book'
    EVENT_SCAN_EXISTING_BOOK_CONFIRM_VOLUME = 'on_scan_existing_book_confirm_volume'
    EVENT_REJECT_BOOK = 'on_reject_book'
    EVENT_RETRIEVAL_ERROR = 'on_retrieval_error'

    current_title = StringProperty()  # Store title of current screen
    screen_names = ListProperty([])
    screens = DictProperty()  # Dict of all screens

    r_popup = ObjectProperty(None)
    si_popup = ObjectProperty(None)
    n_popup = ObjectProperty(None)

    status = NumericProperty(-2)
    sm = ObjectProperty(None)
    response = ObjectProperty(None)

    catalogs = ListProperty(CATALOGS)
    default_catalog = StringProperty(DEFAULT_CATALOG)

    dd_widget = None
    dd_button = None

    book_dir = None

    __events__ = (EVENT_SCAN_BOOK,
                  EVENT_SCAN_EXISTING_BOOK,
                  EVENT_CANNOT_SCAN_BOOK,
                  EVENT_SCAN_EXISTING_BOOK_CONFIRM_VOLUME,
                  EVENT_REJECT_BOOK,
                  EVENT_RETRIEVAL_ERROR,)

    def __init__(self, **kwargs):
        super(WonderfetchDialog, self).__init__(**kwargs)
        self.book_dir = None
        self.r_popup = WonderfetchResultPopup()
        self.r_popup.set_main_widget(self)
        self.n_popup = WonderfetchNotificationPopup()
        self.simple_list_widget = None

        self.load_screens()
        self.go_screen('search', 'left')

    def load_screens(self):
        """
        Load all screens from data/screens to Screen Manager
        :return:
        """
        available_screens = []

        full_path_screens = glob.glob(
                join(dirname(__file__), 'screens/*.kv')
            )

        for file_path in full_path_screens:
            file_name = basename(file_path)
            available_screens.append(file_name.split(".")[0])

        self.screen_names = available_screens
        for i in range(len(full_path_screens)):
            screen = Builder.load_file(full_path_screens[i])
            self.screens[available_screens[i]] = screen

        self.sm = self.ids['sm']
        return True

    def go_screen(self, dest_screen, direction):
        """
        Go to given screen
        :param dest_screen:     destination screen name
        :param direction:       "up", "down", "right", "left"
        :return:
        """
        if dest_screen == 'search':
            self.auto_dismiss = True
            self.screens['search'].ids['_identifier'].text = ''
            self.screens['search'].ids['_volume'].text = ''

        self.sm.transition = SlideTransition()
        screen = self.screens[dest_screen]
        if screen.name != self.current_title:
            self.sm.switch_to(screen, direction=direction)
        self.current_title = screen.name
        if dest_screen == 'search':
            self.screens['search'].ids['_identifier'].focus = True

    def open_search(self, method, identifier, volume='', catalog = None, old_pallet = None):
        self.screens['search'].ids['_identifier'].text = identifier
        self.screens['search'].ids['_volume'].text = volume
        self.method = method
        self.current_catalog = catalog
        self.old_pallet = old_pallet
        self.bind(on_open=self._start_search)
        self.open()

    def _start_search(self, *args):
        self.unbind(on_open=self._start_search)
        self.screens['search'].ids['_button'].trigger_action()

    def create_list_widget(self):
        books_list = {}
        if len(self.response['books']) > 0:
            books_list.update(self.response['books'])
        if len(self.response['related_books']) > 0:
            books_list.update(self.response['related_books'])

        related_books_list = build_list(books_list)
        if related_books_list:
            self.simple_list_widget = SimpleList()
            self.simple_list_widget.leafs = related_books_list
            self.popup = Popup(
                title=self.title, content=self.simple_list_widget, size_hint=(None, None),
                size=('500dp', '700dp'))

            button = ColorButton(text='Click here to see a list of items we have for this book',
                                 size_hint_max_y='30dp',
                                 pos_hint={'center_x': 0.5, 'center_y': 0.5})
            button.bind(on_release=self.popup.open)
            self.r_popup.ids['_extend'].add_widget(button)
            volume = self.screens['search'].ids['_volume'].text or None
            if volume:
                from kivy.uix.label import Label
                label = Label(text='It appears you are working on volume {}.'.format(volume), font_size=20)
                self.r_popup.ids['_extend'].add_widget(label)

    def search(self, wid,):
        ret = None
        try:
            ret = self.search_inner(wid, self.current_catalog, self.old_pallet)

        except Exception as e:
            self.dispatch(self.EVENT_RETRIEVAL_ERROR, e,
                          self.last_concrete_search_id, self.method, self.current_catalog)
        return ret

    def search_inner(self, wid, catalog, old_pallet):
        """
        Send request to the server and parse response.
        :param wid: ColorButton widget itself
        :return:
        """

        _unformatted_id = self.screens['search'].ids['_identifier'].text

        pattern = config.get('wonderfetch_validation_regex', None)

        if pattern:
            match = re.search(pattern, _unformatted_id)
            if not match:
                _id = _unformatted_id
            else:
                _id = match.group()
        else:
            _id = _unformatted_id

        self.screens['search'].ids['_identifier'].text = _id

        wid.disabled = True

        if self.simple_list_widget != None:
            self.r_popup.ids['gr_dd'].clear_widgets()
            self.r_popup.ids['_extend'].clear_widgets()
            self.simple_list_widget = None

        self.last_concrete_search_id = _id

        # result, payload = get_api_result(self.method, _id, catalog=catalog)
        #old_pallet = self.get_val('old_pallet');
        Logger.info('Old pallet is {}'.format(old_pallet));
        result, payload = get_api_result(self.method, _id, catalog=catalog, old_pallet=old_pallet)
        Logger.info('Returned old pallet is {}'.format(payload['old_pallet']));
        if result:
            payload['scribe3_search_catalog'] = payload['normalized_search_key']
            self.response = payload
        else:
            raise payload

        self.status = parse_response(payload)

        if self.status >= 0:

            if self.status != 1:  # remove Dropdown widget which is created in case of response is 1
                if self.dd_button is not None:
                    self.r_popup.ids['gr_dd'].remove_widget(self.dd_button)
                    self.dd_button = None
                    self.dd_widget = None

                # Parse response
            if self.status == 0:   # we don't need this book
                self.r_popup.ids['btn_confirm'].text = 'Scan anyway'
                self.r_popup.ids['button_print_slip'].disabled = False
                if 'books' in self.response:
                    self.create_list_widget()
                self.display_popup("We do not need to scan this book.", self.response.get('keep_dupe_message'))

            elif self.status == 1:   # we need to scan this book
                self.r_popup.ids['btn_confirm'].text = 'Scan this book'
                self.r_popup.ids['button_print_slip'].disabled = True
                self.display_popup("We need to scan this book")

            # we have already scanned this book, but need another physical copy for a partner
            elif self.status == 4:
                self.r_popup.ids['btn_confirm'].text = 'Scan anyway'
                self.r_popup.ids['button_print_slip'].disabled = False
                self.display_popup(self.response.get('message'))
            # we have already scanned this book, but need another physical copy for a partner
            else:
                self.display_popup('Response type {} is not supported. Contact an admin.'.format(self.status))
        else:
            if self.status == -1:
                self.r_popup.ids['btn_confirm'].text = 'Confirm'
                msg = self.response.get('message')
                self.display_popup('Invalid catalog number: [{}]\n {}'.format(_id, msg))
            else:
                self.display_popup("Error {} with the input string or the service.".format( self.status ))

        # Enable new search
        wid.disabled = False


    def btn_retry(self):
        """
        Clear  widget and allow new search
        :return:
        """
        self.go_screen('search', 'left')
        self.r_popup.dismiss()

    def btn_print_do_not_want_slip(self):
        self.r_popup.dismiss(animation=False)
        if self.status == 0:
            Logger.info('Wonderfetch: The user decided to print a slip after the API said we do not want this book')
            current_selector = self.screens['search'].ids['_identifier'].text
            # Just adding this here for debug, temporarily
            if current_selector != self.last_concrete_search_id:
                raise Exception('Conflicting search state, this should not happen')
            self.dispatch(self.EVENT_CANNOT_SCAN_BOOK, self.current_catalog,
                          self.last_concrete_search_id, self.response)
        self.dismiss(animation=False)


    def btn_confirm(self):
        self.r_popup.dismiss(animation=False)
        isbn = self.screens['search'].ids['_identifier'].text
        volume = self.screens['search'].ids['_volume'].text or None
        if self.status == -1:
            self.dismiss()
        elif self.status == 0:
            # Scan anyway
            Logger.info('Wonderfetch: The user decided to scan the book anyway')
            self.dispatch(self.EVENT_SCAN_EXISTING_BOOK_CONFIRM_VOLUME, self.response, isbn, volume)
        elif self.status == 1:
            if isbn:
                Logger.info('Wonderfetch: The user decided to scan the book after '
                            'checking "WE NEED TO SCAN THIS BOOK."')
                self.dispatch(self.EVENT_SCAN_BOOK, self.response, isbn, volume)
            self.dismiss(animation=False)

    def display_popup(self, message, secondary_message=None):
        """
        Display caution popup
        :param message: Content to display
        :return:
        """
        self.r_popup.ids['lb_content'].text = message
        self.r_popup.ids['lb_additional_content'].text = secondary_message if secondary_message else ''
        self.r_popup.open()

    def _book_list_args_converter(self, row_index, x):
        return {'text': x, 'size_hint_y': None, 'height': '30dp'}

    def _real_remove_widget(self):
        self.go_screen('search', 'left')
        super(WonderfetchDialog, self)._real_remove_widget()

    @staticmethod
    def get_val(widget):
        """Wrapper module that returns a MetadataTextInput widget's text
        content
        """
        if isinstance(widget, MetadataTextInput):
            return widget.text
        return None

    @staticmethod
    def set_val(widget, val):
        """Wrapper module that sets a MetadataTextInput widget's text content
        """
        if val is None:
            return
        if isinstance(widget, MetadataTextInput):
            widget.text = val

    def on_scan_book(self, response, isbn, volume):
        pass

    def on_scan_existing_book(self, response, isbn, volume):
        pass

    def on_cannot_scan_book(self, catalog, isbn, response):
        pass

    def on_reject_book(self, isbn, volume):
        pass

    def on_retrieval_error(self, exception, wid, method, catalog):
        pass

    def on_dismiss(self):
        self.current_catalog = None
        self.last_concrete_search_id = None
        super().on_dismiss()

    def on_scan_existing_book_confirm_volume(self, response, isbn, volume):
        extra_data = (isbn, volume)
        popup = self.create_popup(popup_cls=NumberPopup,
                                  value=volume,
                                  extra=extra_data)
        popup.title = 'Confirm volume number'
        popup.none_value_allowed = True
        popup.bind(on_submit=partial(self.on_volume_value_submit, isbn))
        popup.open()

    def on_volume_value_submit(self, isbn, popup, volume,  *args, **kwargs):
        isbn_extra, volume_extra = popup.extra
        vol_val = str(int(volume)) if volume else None
        self.dispatch(self.EVENT_SCAN_EXISTING_BOOK, self.response, isbn, vol_val)
        self.dismiss(animation=False)

    def create_popup(self, **kwargs):
        popup_cls = kwargs.pop('popup_cls', Popup)
        popup = popup_cls(**kwargs)
        return popup


class WonderfetchResultPopup(Popup):
    main_widget = ObjectProperty(None)

    def set_main_widget(self, wid):
        self.main_widget = wid

    def btn_print_do_not_want_slip(self):
        self.main_widget.btn_print_do_not_want_slip()

    # no longer used
    def on_btn_retry(self):
        self.main_widget.btn_retry()

    def on_btn_confirm(self):
        self.main_widget.btn_confirm()

    def on_btn_close(self):
        self.dismiss()
        self.main_widget.dismiss()


class WonderfetchNotificationPopup(Popup):
    pass
