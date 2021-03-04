import os
import webbrowser
from functools import partial

from kivy.clock import Clock
from kivy.compat import text_type
from kivy.lang import Builder
from kivy.properties import BooleanProperty
from kivy.properties import ListProperty, NumericProperty, ObjectProperty, StringProperty, DictProperty
from kivy.uix.behaviors import CompoundSelectionBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.screenmanager import Screen

from ia_scribe.scribe_globals import LOADING_IMAGE
from ia_scribe.tasks.ia_login import IALoginTask
from ia_scribe.tasks.ui_handlers.generic import GenericUIHandler
from ia_scribe.uix.actions.generic import ColoredYesNoActionPopupMixin
from ia_scribe.uix.components.layouts import SelectableGridLayout
from ia_scribe.uix.components.poppers.popups import InfoPopup, QuestionPopup
from ia_scribe.uix_backends.user_switch_backend import UserSwitchScreenBackend
from ia_scribe.utils import get_gravatar_url

Builder.load_file(os.path.join(os.path.dirname(__file__), 'user_switch_screen.kv'))


class UserSwitchScreen(Screen):
    index = NumericProperty(0)
    sections = ListProperty()
    callback = ObjectProperty(None)
    task_scheduler = ObjectProperty()
    recent_operators_list = ListProperty()

    def __init__(self, **kwargs):
        self.backend = UserSwitchScreenBackend()
        self.refresh_users()
        super(UserSwitchScreen, self).__init__(**kwargs)
        Clock.schedule_once(self._postponed_init)

    def _postponed_init(self, *args, **kwargs):
        self.ids.recent_operators_rv.layout_manager.bind(on_left_option_select=self._on_menu_option_selection)
        self.ids.recent_operators_rv.layout_manager.bind(on_right_option_select=self._on_menu_option_selection_rite)
        self.backend.bind(recent_users=self.refresh_users)
        self.ids._login_form.fbind(self.ids['_login_form'].EVENT_LOGIN_USER_SUCCESS, self.save_user_login)

    def _on_menu_option_selection(self,  menu, tile):
        self.show_popup(tile.email, tile.payload)

    def _on_menu_option_selection_rite(self, menu, tile):
        self.show_user_info(tile.email, tile.username)

    def refresh_users(self, *args, **kwargs):
        self.recent_operators_list = self.backend.get_recent_users_list()

    def show_popup(self, email, user_data):
        self.action = ColoredYesNoActionPopupMixin(
            action_function=partial(self.login_user, email, user_data),
            title='Login confirmation',
            message='Would you like to login as\n\n[size=16][b]{}[/b][/size]?'.format(email)
        )
        self.action.display()

    def save_user_login(self, form, email,  payload):
        self.login_user(email, payload)

    def login_user(self, email, payload, *args):
        result, error = self.backend.login_user(email, payload)
        if result:
            self.refresh_users()
            self.manager.transition.direction = 'left'
            self.manager.current = 'upload_screen'
        else:
            popup = InfoPopup(
                title='Login error',
                message='The following error was encountered\n{}'.format(error),
                text_yes='OK',
            )
            popup.open()

    def delete_user(self, meta_popup, popup, email):
        meta_popup.dismiss()
        res = self.backend.delete_user(email)
        if not res:
            popup = InfoPopup(
                title='Error',
                message='Cannot delete current user',
                auto_dismiss=False
            )
            popup.bind(on_submit=popup.dismiss)
            popup.open()

    def show_user_info(self, email, username):
        ts = UserInfoPopup(email =email,
                           username=username,)
        p = Popup(
            title='User details', content=ts, size_hint=(None, None),
            size=('500dp', '250dp')
        )
        ts.fbind('on_delete', self.delete_user, p)
        p.open()


class UserInfoPopup(BoxLayout):
    user_image = StringProperty('user.png')
    username = StringProperty('')
    email = StringProperty(allownone=False)

    __events__ = ('on_delete', )

    def __init__(self, **kwargs):
        super(UserInfoPopup, self).__init__(**kwargs)
        self.user_image = get_gravatar_url(self.email)

    def do_delete(self):
        self.dispatch('on_delete', self.email)

    def on_delete(self, *args, **kwargs):
        pass


class RecentOperatorsWidget(RecycleView):
    def __init__(self, **kwargs):
        super(RecentOperatorsWidget, self).__init__(**kwargs)


class UserTileContainer(SelectableGridLayout):

    __events__ = ('on_left_option_select', 'on_right_option_select')

    def add_widget(self, widget, index=0):
        if isinstance(widget, UserTileView):
            widget.fbind('on_left_selection', self.select_left)
            widget.fbind('on_right_selection', self.select_right)
        super(UserTileContainer, self).add_widget(widget, index)

    def remove_widget(self, widget):
        if isinstance(widget, UserTileView):
            widget.funbind('on_left_selection', self.select_left)
            widget.funbind('on_right_selection', self.select_right)
        super(UserTileContainer, self).remove_widget(widget)

    def select_left(self, tile):
        self.dispatch('on_left_option_select', tile)

    def select_right(self, tile):
        self.dispatch('on_right_option_select', tile)

    def on_left_option_select(self, *args, **kwargs):
        pass

    def on_right_option_select(self, *args, **kwargs):
        pass


class UserTileView(RecycleDataViewBehavior, BoxLayout):
    index = NumericProperty()
    email = StringProperty(allownone=False)
    username = StringProperty()
    payload = DictProperty()
    is_active_user = BooleanProperty(False)
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)
    user_image = StringProperty('user.png')

    __events__ = ('on_left_selection', 'on_right_selection')

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        if data.get('payload'):
            if 'general' in data.get('payload'):
                general_section = data.get('payload')['general']
                self.username = general_section['screenname'] if 'screenname' in general_section else ''
        if data.get('is_active_user'):
            self.bgcol = [0, 0.28, 0.42, .5]
        self.user_image = get_gravatar_url(data.get('email'))
        return super(UserTileView, self).refresh_view_attrs(
            rv, index, data)

    def on_touch_down(self, touch):
        if self.disabled and self.collide_point(*touch.pos):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            self.bgcol = [0, 0.28, 0.42, 1]
            touch.grab(self)
            self.selected = True
            return True

    def on_touch_move(self, touch):
        return touch.grab_current is self

    def on_touch_up(self, touch):
        if self.disabled and self.collide_point(*touch.pos):
            if touch.grab_current is self:
                touch.ungrab(self)
            return True
        if touch.grab_current is self:
            touch.ungrab(self)

            if self.is_active_user:
                self.bgcol = [0, 0.28, 0.42, .5]
            else:
                self.bgcol = [1, 1, 1, 1]

            parent = self.parent
            if isinstance(parent, CompoundSelectionBehavior):
                if self.collide_point(*touch.pos):
                    if touch.button == 'left':
                        self.dispatch('on_left_selection')
                    elif touch.button == 'right':
                        self.dispatch('on_right_selection')
            self.selected = False
            return True

    def on_left_selection(self):
        pass

    def on_right_selection(self):
        pass


class LoginForm(BoxLayout):
    email = StringProperty(None)

    EVENT_LOGIN_USER_START = 'on_event_login_user_start'
    EVENT_LOGIN_USER_SUCCESS = 'on_event_login_user_success'
    EVENT_LOGIN_USER_FAILURE = 'on_event_login_user_failure'

    __events__ = (EVENT_LOGIN_USER_START,
                  EVENT_LOGIN_USER_FAILURE,
                  EVENT_LOGIN_USER_SUCCESS )

    load_img = Image(source=LOADING_IMAGE)
    task_scheduler = ObjectProperty()

    def __init__(self, **kwargs):
        super(LoginForm, self).__init__(**kwargs)

    @staticmethod
    def archive_signup():
        webbrowser.open("https://archive.org/account/login.createaccount.php")

    @staticmethod
    def archive_forgot_pwd():
        webbrowser.open("https://archive.org/account/login.forgotpw.php")

    def _is_valid(self, creds):
        return len(creds['email']) and len(creds['password']) > 0

    def login(self):
        creds = {'email': self.ids['_login_email_input'].text,
                 'password': self.ids['_login_password_input'].text}
        if self._is_valid(creds):
            self.email = creds['email']
            self.password = creds['password']
            self.dispatch(self.EVENT_LOGIN_USER_START)
        else:
            self.show_popup('invalid credentials',
                            'The credentials you inserted are invalid.\n'
                            'Please check your username and password and try again.')

    def on_event_login_user_start(self):
        task_handler = GenericUIHandler(
            task_type=IALoginTask,
            email=self.email,
            password=self.password,
            callback=self.post_login)
        self.task_scheduler.schedule(task_handler.task)

    def post_login(self, result, error):
        if not error:
            self.dispatch(self.EVENT_LOGIN_USER_SUCCESS, self.email, result)
        else:
            msg = text_type(error)
            self.dispatch(self.EVENT_LOGIN_USER_FAILURE, self.email, msg)
        self.email = self.password = ''

    def on_event_login_user_failure(self, email, msg):
        self.show_popup("Log in error",
                        "Couldn't log in.\n\nPlease check your credentials and\n"
                        "internet connectivity and try again.\nError:\n" + msg)

    def on_event_login_user_success(self, email, payload):
        pass


    def show_popup(self,title, label):
        popup = InfoPopup(
            title=title,
            message=(label),
            auto_dismiss=False
        )
        popup.bind(on_submit=popup.dismiss)
        popup.open()


