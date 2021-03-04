import pickle
import codecs
import textwrap
import time
from functools import partial

from twisted.internet import reactor, protocol, ssl
from twisted.words.protocols import irc

from cli import cli
from ia_scribe.abstract import Singleton, Observable
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.utils import get_scanner_property
from ia_scribe import scribe_globals
from ia_scribe.ia_services.c2_registration import verify_registration

from kivy.app import App
from kivy import Logger

config = Scribe3Configuration()

registration_ok, registration_error = verify_registration()

DEFAULT_CHANNELS = ['all', 'control']
SCANCENTER_CHANNEL = get_scanner_property('scanningcenter')
CHANNELS_TO_JOIN = DEFAULT_CHANNELS + [SCANCENTER_CHANNEL]
C2_SERVER = config.get('c2_server', scribe_globals.C2_SERVER)
C2_SERVER_PORT = config.get('c2_server_port', scribe_globals.C2_SERVER_PORT)
C2_NAME = config.get('c2_name')
C2_PASSWORD = config.get('c2_password')

app = App.get_running_app()

REMOTE_ONLY_COMMANDS = {
    'screenshot': app.get_screenshot_as_bytes,
    'current_screen': app.get_current_screen,
    'task_scheduler': partial(cli.abstract_handler, app.task_scheduler)

}

class LogBot(irc.IRCClient):
    nickname = C2_NAME
    password = C2_PASSWORD

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.factory.app.message_callback("[connected at %s]" %
                                          time.asctime(time.localtime(time.time())))
        self.factory.app.on_connection(self)

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        self.factory.app.message_callback("[disconnected at %s]" %
                                          time.asctime(time.localtime(time.time())))

    # callbacks for events

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        for channel in self.factory.channels:
            self.join(channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.factory.app.message_callback("[I have joined %s]" % channel)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]
        Logger.debug('{}->{}: {}'.format(user, channel, msg))
        #self.factory.app.message_callback("<%s> %s" % (user, msg))
        try:
            self._handle_privmsg(user, channel, msg)
        except Exception as e:
            Logger.error('{}->{}: {} | {}'.format(user, channel, msg, e))

    def _handle_privmsg(self, user, channel, msg):
        if user == 'NickServ':
            if msg == 'Login failed.  Goodbye.':
                self.quit()
                return

        if channel == '#control':
            if self.nickname in msg:
                token = msg.split('/')[1]
                command_string = msg.split(self.nickname)[1:][0]
                self.handle_command(command_string, channel, token)
            return

        # Check to see if they're sending me a private message
        if channel == self.nickname:
            token = msg.split('/')[1]
            msg = msg.split('/')[2]
            self.handle_command(msg, user, token)
            return

        if channel == '#{}'.format(SCANCENTER_CHANNEL):
            self.factory.app.message_callback("[Scancenter] <%s> %s" % (user, msg))
            return

    def handle_command(self, message, sender, token):
        cleaned_message = message.lstrip(' ')
        command = cleaned_message.split(' ')
        msg = "Received your command {}, {}".format(command, sender)
        #self.msg('room', msg)
        # self.factory.app.message_callback('Received command {} from {}'.format(command, user))
        self.factory.app.dispatch_commands(command, sender, token)
        return

    def alterCollidedNick(self, nickname):
        return nickname + '_'

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        self.factory.app.message_callback("* %s %s" % (user, msg))

    @staticmethod
    def split(str, token, length=80):
        val = ['/{}/{}'.format(token, chunk)
                for line in str.split('\n')
                for chunk in textwrap.wrap(line, length - 12 - len(token))]


        return val

    def msg(self, token, user, message, length=None):
        fmt = 'PRIVMSG %s :' % (user,)

        if length is None:
            length = self._safeMaximumLineLength(fmt)

        # Account for the line terminator.
        minimumLength = len(fmt) + 2
        if length <= minimumLength:
            raise ValueError("Maximum length must exceed %d for message "
                             "to %s" % (minimumLength, user))


        lines_accumulator = []
        for line in self.split(message, token, length - minimumLength):
            lines_accumulator.append(fmt + line)
        if len(lines_accumulator) > 1:
            header = '/{}/^PREAMBLE^{}'.format(token, len(lines_accumulator))
            self.sendLine(fmt + header)
        for line in lines_accumulator:
            self.sendLine(line)


class LogBotFactory(protocol.ClientFactory):
    """A factory for LogBots.

    A new protocol instance will be created each time we connect to the server.
    """
    protocol = LogBot

    def __init__(self, app, channels_list):
        self.app = app
        self.channels = channels_list

    def startedConnecting(self, connector):
        #self.app.message_callback('Started to connect.')
        pass

    def clientConnectionLost(self, connector, reason):
        self.app.message_callback('Lost connection: {}'.format(reason))
        retry_timeout = config.get_numeric_or_none('c2_retry_timeout')
        if retry_timeout:
            reactor.callLater(retry_timeout, connector.connect)
        else:
            reactor.stop()

    def clientConnectionFailed(self, connector, reason):
        self.app.message_callback('Connection failed: {}'.format(reason))
        retry_timeout = config.get_numeric_or_none('c2_retry_timeout')
        if retry_timeout:
            reactor.callLater(retry_timeout, connector.connect)
        else:
            reactor.stop()


class S3C2(Singleton, Observable):
    connection = None
    callback = None
    observers = set([])

    def build(self):
        self.connect_to_server()

    def connect_to_server(self):
        hostname = C2_SERVER
        port = C2_SERVER_PORT
        f = LogBotFactory(self, CHANNELS_TO_JOIN)
        reactor.connectSSL(hostname, port, f, ssl.ClientContextFactory())

    def disconnect(self):
        self.connection.quit()

    def on_connection(self, connection):
        self.message_callback("Connected successfully!")
        self.connection = connection

    def message_callback(self, msg):
         print("{}\n".format(msg))
         self.notify(msg)
         if self.callback:
             self.callback(message=msg)

    def dispatch_commands(self, commands, from_user, token):
        command = args = None
        if type(commands) is not list:
            return
        if len(commands) == 0:
            return
        if len(commands) >= 1:
            command = commands[0].strip(' ')
        if len(commands) > 1:
            args = commands[1:]

        if command in ['notifications', 'metadata', 'exit']:
            result = self.encode('''Module {} is not yet supported remotely and is only available through the CLI.'''.format(command))
        elif command in REMOTE_ONLY_COMMANDS:
            if args:
                result = self.encode(REMOTE_ONLY_COMMANDS[command](*args))
            else:
                result = self.encode(REMOTE_ONLY_COMMANDS[command]())
        else:
            result = self.encode(cli.evaluate(command, args))
        self.connection.msg(token, from_user, result)

        command_cycle = '{}> {} ({})'.format(from_user, commands, len(result))
        self.notify(command_cycle)

    @staticmethod
    def encode(obj):
        pickled_object = pickle.dumps(obj, protocol=scribe_globals.PICKLE_PROTOCOL)
        ret = codecs.encode(pickled_object, "base64").decode()
        return ret
