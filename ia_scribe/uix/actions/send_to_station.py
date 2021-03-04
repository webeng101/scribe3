from ia_scribe.uix.actions.helpers import PopupCreator
from ia_scribe.uix.actions.error import ShowErrorAction
from ia_scribe.uix.actions.info import ShowInfoActionPopupMixin
from ia_scribe.ia_services import btserver
from ia_scribe.uix.components.messages.messages import ScribeMessageGenericContent
from ia_scribe.uix.components.buttons.buttons import RadioButton

from ia_scribe.config.config import Scribe3Configuration
config = Scribe3Configuration()


class SendToStationActionMixin(PopupCreator):

    def __init__(self, **kwargs):
        self.book = kwargs.pop('book')
        super(SendToStationActionMixin, self).__init__(**kwargs)
        self.scancenter, self.stations_list = self._get_data()
        popup_content = self._build_content()
        self.popup_args = {'title': 'Send to another station in {}'.format(self.scancenter),
                           'content': popup_content,
                           'auto_dismiss': False,
                           'title_size': '18sp',
                           'size_hint_x': None,
                           'size_hint_y': 0.6,
                           'width': '400dp'}
        self.create_popup(**self.popup_args)
        popup_content.popup = self.popup

    @staticmethod
    def _get_data():
        show_all = config.is_true('send_to_all_stations')
        sc, stations_list = btserver.get_adjacent_scanners(show_all)
        if not sc:
            raise Exception('Could not retrieve stations list. Please try again later.')
        return sc, stations_list

    def _build_content(self):
        selected_target_station = self.book.get_foldout_target()
        content = ScribeMessageGenericContent()
        for item in self.stations_list:
            active_value = selected_target_station == item
            selectable_option = RadioButton(
                text=item,
                group='scanners',
                active=active_value
            )
            content.ids._content.add_widget(selectable_option)
        content.ok_text = 'Send'
        content.ids._ok_button.background_color = [1, 0, 0, 1]
        content.trigger_func = self.do_action
        return content

    def do_action(self, popup, *args, **kwargs):
        target_scanner = None
        for button in popup.content.ids._content.children:
            if button.active:
                target_scanner = button.text

        if not target_scanner:
            self.action = ShowErrorAction(message='You need to select a station')
            self.action.display()
            return

        self.book.set_foldout_target(target_scanner)
        self.action = ShowInfoActionPopupMixin(message='Okay, upon [u]upload[/u] [b]{}[/b] '
                                             'will be sent to [b]{}[/b] for foldouts.'.format(self.book.name_human_readable(),
                                                                                       target_scanner))
        self.action.display()
        self.popup.dismiss()
