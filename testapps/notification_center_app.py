from kivy.app import App
from kivy.properties import ObjectProperty

from ia_scribe.notifications.notifications_manager import NotificationManager
from ia_scribe.uix.widgets.notification_center.notification_center import \
    NotificationCenterWidget


class NotificationCenterApp(App):
    nm = ObjectProperty()

    def build(self):
        root = NotificationCenterWidget(
                                        pos_hint={'x': 0.0, 'center_y': 0.5},
                                        size_hint=(1.0, 1.0)
                                        )
        return root

    def on_start(self):
        super(NotificationCenterApp, self).on_start()
        self.root_window.size = (1000, 600)
        self.nm = NotificationManager()
        self.create_dummy_notifications()
        self.root.attach(self.nm, book_handler=self.book_handler)

    @staticmethod
    def book_handler(*args):
        pass

    def create_dummy_notifications(self):
        self.nm.add_notification(title='Test 1', message='Test notification ' * 20)
        self.nm.add_notification(title='Test 1', message='')
        self.nm.add_notification(title='Command and control', message='I have connected')
        self.nm.add_notification(title='Command and control', message='I have Joined a channel')
        self.nm.add_notification(title='Command and control', message='I have done something else')
        self.nm.add_notification(title='Command and control', message='I have just received a message from someone')
        self.nm.add_notification(title='A rather long title for a notification, that is for sure',
                                 message='I have just recieved a message from Central Command')

        self.nm.add_notification(title='Test 2', message='This is a book notification' * 10, book=object)
        self.nm.add_notification(title='Test 3', message='This is a system error notification' * 30, is_error=True)
        self.nm.add_notification(title='Test 4', message='This is a book error notification',  book=object, is_error=True)
        for i in range(1, 30):
            self.nm.add_notification(title='AUtomated test notification number {}'.format(i), message='Automated notification')
        msg = '''Distinctio rem tenetur cumque. Est dicta dolores necessitatibus laudantium. Optio consequatur provident voluptatibus. Quia architecto debitis error. Eveniet expedita quia odio culpa. Cumque inventore voluptate reprehenderit. Repellat aut molestias natus. Magnam nihil nam delectus sit distinctio earum non fuga. Est fugit quia a architecto sit expedita. Non voluptas dolores voluptatem quia enim. Est autem ut ratione modi nisi. Debitis dolorem quae vero qui aut laboriosam. Non dolorem sit suscipit eligendi. Vel nihil consequatur numquam. Tenetur est placeat dignissimos voluptas corrupti voluptatem doloribus. Sed eligendi ducimus eveniet itaque dolorem eum sunt. Similique et suscipit ut perspiciatis et omnis. Itaque occaecati commodi rerum doloremque non quis ut voluptatem. Harum tempore officiis et atque animi possimus. Et reiciendis quis molestiae qui voluptatem adipisci aperiam. Dolorem natus officia impedit. Cupiditate aspernatur doloremque harum ex reiciendis est. '''
        self.nm.add_notification(title='Sticky notifcation', message=msg, is_sticky=True)


if __name__ == '__main__':
    NotificationCenterApp().run()
