# install_twisted_rector must be called before importing the reactor


from kivy.support import install_twisted_reactor

install_twisted_reactor()

# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, ssl
from twisted.python import log

# system imports
import time, sys, unicodedata, os
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
os.environ['DISPLAY'] = ':0'

class LogBot(irc.IRCClient):
    nickname = 'davide-dev.sanfrancisco.archive.org'  # nickname
    password = 'passie'  # server pass

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.factory.app.message_callback("[connected at %s]" %
                                          time.asctime(time.localtime(time.time())))
        self.factory.app.on_connection(self)

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        self.factory.app.message_callback("[disconnected at %s]" %
                                          time.asctime(time.localtime(time.time())))
        self.logger.close()

    # callbacks for events

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.factory.app.message_callback("[I have joined %s]" % self.factory.channel)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]
        self.factory.app.message_callback("<%s> %s" % (user, msg))

        if msg.startswith(self.nickname):
            command = msg.split(self.nickname)[1:]
            msg = "Received your command {}, {}".format(command, user)
            self.say('room', msg)
            self.factory.app.message_callback('Received command {} from {}'.format(command, user))
            self.factory.app.dispatch_command(command, user)
            return

        # Check to see if they're sending me a private message
        if channel == self.nickname:
            msg = "Received your command {}, {}".format(msg, user)
            self.msg(user, msg)
            return

        # Otherwise check to see if it is a message directed at me
        if msg.startswith(self.nickname + ":"):
            msg = "%s: I am a log bot" % user
            self.msg(channel, msg)
            self.factory.app.message_callback("<%s> %s" % (self.nickname, msg))

    def alterCollidedNick(self, nickname):
        return nickname + '_'

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        self.factory.app.message_callback("* %s %s" % (user, msg))

    # irc callbacks

    def irc_NICK(self, prefix, params):
        """Called when an IRC user changes their nickname."""
        old_nick = prefix.split('!')[0]
        new_nick = params[0]
        self.factory.app.message_callback("%s is now known as %s" % (old_nick, new_nick))

    # For fun, override the method that determines how a nickname is changed on
    # collisions. The default method appends an underscore.
    def alterCollidedNick(self, nickname):
        """
        Generate an altered version of a nickname that caused a collision in an
        effort to create an unused related name for subsequent registration.
        """
        return nickname + '^'


class LogBotFactory(protocol.ClientFactory):
    """A factory for LogBots.

    A new protocol instance will be created each time we connect to the server.
    """
    protocol = LogBot

    def __init__(self, app, channel, filename):
        self.app =  app
        self.channel = channel
        self.filename = filename

    def startedConnecting(self, connector):
        self.app.message_callback('Started to connect.')

    def clientConnectionLost(self, connector, reason):
        self.app.message_callback('Lost connection.')
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        self.app.message_callback('Connection failed.')
        reactor.stop()

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout


# A simple kivy App, with a textbox to enter messages, and
# a large label to display all the messages received from
# the server
class TwistedClientApp(App):
    connection = None
    textbox = None
    label = None

    def build(self):
        root = self.setup_gui()
        self.connect_to_server()
        return root

    def setup_gui(self):
        self.textbox = TextInput(size_hint_y=.1, multiline=False)
        self.textbox.bind(on_text_validate=self.send_message)
        self.label = Label(text='connecting...\n')
        layout = BoxLayout(orientation='vertical')
        layout.add_widget(self.label)
        layout.add_widget(self.textbox)
        return layout

    def connect_to_server(self):
        log.startLogging(sys.stdout)
        hostname = 'davide-dev.us.archive.org'  # irc-server-hostname
        port = 7777
        f = LogBotFactory(self, 'room', 'room')
        reactor.connectSSL(hostname, port, f, ssl.ClientContextFactory())

    def on_connection(self, connection):
        self.message_callback("Connected successfully!")
        self.connection = connection

    def send_message(self, *args):
        msg = self.textbox.text
        if msg and self.connection:
            self.connection.say('room', msg.encode('utf-8'))
            self.textbox.text = ""

    def message_callback(self, msg):
        self.label.text += "{}\n".format(msg)

    def dispatch_command(self, command, user):
        if type(command) == list and len(command) > 0:
            if command[0] == ' get_books_list':
                from ia_scribe.book.library import Library
                l = Library()
                blist = l.get_all_books()
                msg = str(list(blist))
                self.connection.msg(user, msg.encode('utf-8'))
                self.message_callback('Sent information about {} books in library'.format(len(blist)))

if __name__ == '__main__':
    TwistedClientApp().run()