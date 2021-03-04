import os
import threading
import urllib
import webbrowser
from functools import partial

import internetarchive
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import BooleanProperty
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup

from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.exceptions import ScribeException
from ia_scribe.scribe_globals import LOADING_IMAGE
from ia_scribe.uix.actions.info import ShowInfoActionPopupMixin
from ia_scribe.uix.screens.wizard.sections.base import BaseSection
from ia_scribe.utils import restart_app
from ia_scribe.tasks.ia_login import IALoginTask
from ia_scribe.tasks.ui_handlers.generic import GenericUIHandler
from ia_scribe.uix.actions.error import ShowErrorAction

Builder.load_file(os.path.join(os.path.dirname(__file__), 'kv', 'login.kv'))

config = Scribe3Configuration()


class LoginSection(BaseSection):

    load_img = Image(source=LOADING_IMAGE)
    success = BooleanProperty(False)

    en_next_button = False

    def __init__(self, **kwargs):
        self.task_scheduler = kwargs.pop('task_scheduler')
        super(LoginSection, self).__init__(**kwargs)


    def on_enter(self):
        super(LoginSection, self).on_enter()

    # Login with archive.org, get s3 keys, store them, done
    # main thread, called by _login_button
    def archive_login(self):
        email = self.ids['_login_email_input'].text
        password = self.ids['_login_password_input'].text
        task_handler = GenericUIHandler(
            task_type=IALoginTask,
            email=email,
            password=password,
            callback=self.post_login)
        self.task_scheduler.schedule(task_handler.task)

    def post_login(self, result, error):
        if error:
            self.action = ShowErrorAction(title='Login error',
                                          message=error,)
            self.action.display()
        else:
            # here it calls update_config, and if we write successfully
            if self.update_config(result) is True:
                self.success = True
                success_message = "You are now logged in as: \n\n" + str(
                    urllib.parse.unquote(result.get("cookies")["logged-in-user"])) + "."
                self.action = ShowInfoActionPopupMixin(message=success_message,
                                                       on_popup_dismiss=self.post_login_confirmation)
                self.action.display()

    def post_login_confirmation(self, *args):
        self.root_widget.go_next()

    def before_next(self):
        self.schedule_rcs_download()
        return True

    @staticmethod
    def archive_signup():
        webbrowser.open("https://archive.org/account/login.createaccount.php")

    @staticmethod
    def archive_forgot_pwd():
        webbrowser.open("https://archive.org/account/login.forgotpw.php")

    # A little wrapper that updates the s3 configuration in scribe_config.yml
    def update_config(self, keys):
        config.set("s3/access_key", str(keys['s3']['access']))
        config.set("s3/secret_key", str(keys['s3']['secret']))

        # get email and escape @
        email = urllib.parse.unquote(keys.get("cookies")["logged-in-user"])
        config.set( "email", email)
        config.set( "cookie", str(keys.get("cookies")["logged-in-sig"]))
        return True

    def on_touch_down(self, touch):
        local_pos = self.to_local(*touch.pos)
        if self.ids['lb_forgot_pwd'].collide_point(*local_pos):
            self.archive_forgot_pwd()
        elif self.ids['lb_signup'].collide_point(*local_pos):
            self.archive_signup()
        super(LoginSection, self).on_touch_down(touch)

    def schedule_rcs_download(self):
        rcs_manager = self.root_widget.sections[3].children[0].rcs
        rcs_manager.attach_scheduler(self.task_scheduler)
        rcs_manager._do_sync()

    # delete s3 keys and account information from scribe_config.yml
    # main thread called by _logout_button
    def archive_logout(self):

        try:
            config.delete('s3')
            config.delete('email')
            config.delete('cookie')
            popup_success = Popup(title='Logged out',
                                  content=Label(text="You have logged out" + ". \n\nRestarting the application..."),
                                  auto_dismiss=True, size_hint=(None, None), size=(400, 200))
            popup_success.open()
            restart_app()
        except:
            # if the keys didn't exist in the first place, a field was missing or whatever, cry.
            raise ScribeException('There was an error logging out.')
