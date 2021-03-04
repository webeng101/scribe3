

from functools import partial
from pprint import pformat

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.shortcuts import clear

from ia_scribe.book.automata import move_along
from ia_scribe.book.library import Library
from ia_scribe.book.book import Book
from ia_scribe.breadcrumbs import api as metrics_api
from ia_scribe.breadcrumbs import other_stats
from ia_scribe.cameras.optics import Cameras
from ia_scribe.config.config import Scribe3Configuration
from ia_scribe.notifications.notifications_manager import NotificationManager
from ia_scribe.update.update import UpdateManager
from ia_scribe.utils import restart_app, restart_process
from ia_scribe.book import metadata
from ia_scribe.ia_services.rcs import RCS

cameras = Cameras()
config = Scribe3Configuration()
library = Library()
notification_manager = NotificationManager()
update_manager = UpdateManager()
rcs_manager = RCS()

ALLOWED_TOKENS = ['help', 'print', 'clear', 'exit', 'library', 'book', 'telemetry', 'metadata', 'rcs',
                  'config', 'move_along', 'notifications', 'cameras', 'stats', 'update', 'restart', ]


def _get_commands(module):
    return ['{}'.format(x) for x in dir(module) if not str(x).startswith('_') and callable(getattr(module, x))]


# takes an object and a string, runs the string as a function and passes args if present
def instance_handler(instance, sub_command, *args):
    try:
        rtm = getattr(instance, str(sub_command))
        if args and len(args) >= 1:
            res = rtm(*args)
        else:
            res = rtm()
    except Exception as e:
        res = 'EXCEPTION, YOUR HONOR! -> {} '.format(sub_command), e
    return res


def abstract_handler(instance, *args):
    if len(args) == 0:
        return {'commands': _get_commands(instance)}
    if len(args) == 1:
        return instance_handler(instance, args[0])
    else:
        return instance_handler(instance, args[0], *args[1:])


library_handler = partial(abstract_handler, library)
config_handler = partial(abstract_handler, config)
cameras_handler = partial(abstract_handler, cameras)
telemetry_handler = partial(abstract_handler, other_stats)
metadata_handler = partial(abstract_handler, metadata)
update_handler = partial(abstract_handler, update_manager)
rcs_handler = partial(abstract_handler, rcs_manager)

def book_handler(*args):
    if len(args) == 0:
        ret = {'usage': 'book <uuid>',
               'commands': _get_commands(Book)}
        return ret
    if len(args) == 1:
        book = library.get_book(args[0])
        return instance_handler(book, 'as_dict')
    else:
        book = library.get_book(args[0])
        return instance_handler(book, args[1], *args[2:])


def move_along_handler(*args):
    if len(args) == 0:
        ret = {'usage': 'move_along <book uuid>',
               }
        return ret
    if len(args) == 1:
        book = library.get_book(args[0])
        return move_along(book)


def stats_handler(*args):
    if config.is_true('stats_disabled'):
        ret = {'error': 'Stats are disabled on this instance.', }
        return ret
    if len(args) == 0:
        return {'commands': _get_commands(metrics_api)}
    if len(args) == 1:
        return instance_handler(metrics_api, args[0])
    else:
        return instance_handler(metrics_api, args[0], *args[1:])

def notification_handler(*args):
    if len(args) == 0:
        ret = {'commands': _get_commands(notification_manager)}
        return ret
    if len(args) == 1:
        return list(instance_handler(notification_manager, args[0]))
    else:
        return list(instance_handler(notification_manager, args[0], *args[2:]))

def restart_handler(*args):
    if len(args) == 0:
        ret = {'usage': 'restart <subcommand>',
               'commands': ['app', 'process']}
        return ret
    if len(args) == 1:
        if args[0] == 'app':
            restart_app()
        elif args[0] == 'process':
            restart_process()
        else:
            return 'Invalid command'

def park_handler(*args):
    if len(args) >= 1:
        if args[0] == 'security':
            return 'access: PERMISSION DENIED.'
        elif args[0] == 'main':
            if len(args) == 3 and args[1] == 'security' and args[2] == 'grid':
                return 'access: PERMISSION DENIED....and...\n' \
                           'YOU DIDNT SAY THE MAGIC WORD!'

    return ['command invalid']



command_handlers = {
    'book': book_handler,
    'library': library_handler,
    'config': config_handler,
    'move_along': move_along_handler,
    'notifications': notification_handler,
    'cameras': cameras_handler,
    'stats': stats_handler,
    'telemetry': telemetry_handler,
    'metadata': metadata_handler,
    'update': update_handler,
    'restart': restart_handler,
    'rcs': rcs_handler,
    'access': park_handler,
}


class Scribe3Completer(Completer):
    def get_completions(self, document, complete_event):
        compl = []
        command, args = lex(tokenize(document.text))
        module_info = command_handlers[command]()
        commands = module_info.get('commands')
        if command in ['book', 'move_along']:
            if len(args) in [0, 1]:
                for entry in library.get_all_books():
                    yield Completion('{}'.format(entry.uuid),
                                     display_meta='{}'.format(entry.status))
            elif len(args) == 2:
                for entry in commands:
                    yield Completion(entry)
        else:
            if len(args) <= 1:
                for entry in commands:
                    yield Completion(entry)


def tokenize(expressiom):
    if ' ' not in expressiom:
        return [expressiom]
    else:
        return expressiom.split(' ')


def lex(tokens):
    command = tokens[0]
    args = tokens[1:]
    if command not in ALLOWED_TOKENS and command != 'access':
        return False, 'Invalid command'
    return command, args


def evaluate(command, args):
    res = None
    global library

    if command == 'print':
        res = args
    elif command == 'help':
        res = render_help_text()
    elif command == 'clear':
        clear()
    elif command == 'exit':
        res = 'Press CTRL + D to exit'
    else:
        res = dispatch(command, args)

    return res

def dispatch(command, args):
    dispatcher = command_handlers[command]
    if args is None:
        args = []
    return dispatcher(*args)


def render_help_text():
    ret = {'message': 'This is the help function of Scribe3 CLI. Welcome!',
           'usage': '''The book command takes a book class method name as second parameter and any subsequent argument will be passed to this downstream method.''',
           'allowed_commands': ALLOWED_TOKENS
           }
    return ret


def entry_point(*args, **kwargs):
    session = PromptSession()

    while True:
        try:
            expression = session.prompt('Scribe3> ', completer=Scribe3Completer())
        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        else:
            tokens = tokenize(expression)
            command, args = lex(tokens)
            if not command:
                print('%> {}'.format(args))
                continue
            else:
                try:
                    result = evaluate(command, args)
                except Exception as e:
                    result = e
                print('%> {}'.format(pformat(result)))
    print('Goodbye!')


if __name__ == '__main__':
    entry_point()
