import copy
import datetime
import hashlib
import logging
import os
import sys
import serial
import subprocess

import internetarchive as ia
from kivy.logger import Logger

from ia_scribe import scribe_globals
from ia_scribe.book.metadata import get_metadata
from ia_scribe.config.config import Scribe3Configuration

config = Scribe3Configuration()

def get_local_settings():
    EXCLUDE_KEYS = ['cookie', 's3', 'c2_password']
    current_config = config.dump()
    all_settings = copy.deepcopy(current_config)
    for key in EXCLUDE_KEYS:
        if key in all_settings:
            del all_settings[key]
    return all_settings

def setup_logger(logger_name, log_file, kivy_logger):
    formatter = logging.Formatter('%(asctime)s : %(message)s')
    fileHandler = logging.FileHandler(
        os.path.join(log_file, logger_name),
        mode='a+')
    fileHandler.setFormatter(formatter)

    kivy_logger.addHandler(fileHandler)

    return fileHandler


def teardown_logger(file_handler, kivy_logger):
    try:
        kivy_logger.removeHandler(file_handler)
        return True
    except:
        return False


def restart_process():
    path = os.path.join(scribe_globals.CONFIG_DIR, 'scribe_pid')
    if os.path.exists(path):
        f = open(path)
        old_pid = f.read().strip()
        f.close()
        pid_dir = os.path.join('/proc', old_pid)
        if os.path.exists(pid_dir):
            Logger.debug('restart_app: Got the pid file at {0}. Now unlinking '
                         'before relaunch...'.format(pid_dir))
            os.unlink(path)
    python = sys.executable
    os.execl(python, python, *sys.argv)

def restart_app():
    # before leaving, remove the current pid lock.
    path = os.path.join(scribe_globals.CONFIG_DIR, 'scribe_pid')
    if os.path.exists(path):
        f = open(path)
        old_pid = f.read().strip()
        f.close()
        pid_dir = os.path.join('/proc', old_pid)
        if os.path.exists(pid_dir):
            Logger.debug('restart_app: Got the pid file at {0}. Now unlinking '
                         'before relaunch...'.format(pid_dir))
            os.unlink(path)
    from kivy.app import App
    app = App.get_running_app()
    app.needs_restart = True
    app.stop()
    #python = sys.executable
    #os.execl(python, python, *sys.argv)


def toast_notify(toast_message, toast_title='Scribe3'):
    toast_icon = os.path.abspath('assets/images/ia_logo_trans_icon.ico')
    try:
        subprocess.call(
            ['notify-send', '-i', toast_icon, toast_title, toast_message]
        )
    except Exception:
        Logger.warning('Problem issuing notification. '
                       'Is notify-send installed on your system?')


def ensure_dir_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)


def has_free_disk_space(path):
    command = ["df " + path + "|tail -1|awk '{print $5}'| sed s/%//"]
    Logger.info('has_free_disk_space: Testing {} -> {}'.format(
        path, 
        ' '.join(command)
    ))
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        shell=True
    )
    (out, err) = process.communicate()
    Logger.info('has_free_disk_space: out -> {} | err -> {}'.format(out, err))
    return int(out) <= 95 if out else False


def read_book_identifier(book_path, identifier_filename='identifier.txt'):
    '''Reads book identifier from file and returns it. If file is missing or
    empty `None` is returned.

    :param book_path: Path to book. Can be `None` or empty `str`
    :param identifier_filename: Defaults to `identifier.txt`
    :return: `None` or identifier (str)
    '''
    identifier = None
    if book_path and identifier_filename:
        identifier_path = os.path.join(book_path, identifier_filename)
        if os.path.exists(identifier_path):
            with open(os.path.join(book_path, identifier_filename)) as fp:
                identifier = fp.read().strip()
    return identifier


def compress_logs_dir(directory = '~/.kivy', duration= '2', file_name='scribe3_log'):
    def directory_upsert(directory):
        path = os.path.expanduser(directory)
        storage_path = os.path.join(path, 'logs_storage')
        if not os.path.exists(storage_path):
            print("created dir", storage_path)
            os.mkdir(storage_path)
        print('upsert: returning', path, storage_path)
        return path, storage_path

    print('checking for directory')
    path, storage_path = directory_upsert(directory)
    filename = '{}_{:%Y-%m-%d%H:%M:%S}.tar.gz'.format(file_name, datetime.datetime.now())
    destfile_path = os.path.join(os.path.expanduser(storage_path), filename)
    command = "find {source_path}/logs/* +mtime {duration} | while read filename ; do fuser -s $filename " \
              "| echo $filename ; done | xargs tar --remove-files -czvPf {destfile_path}  --transform 's/.*\///g' "\
        .format(source_path = path,
                duration = duration,
                filename = filename,
                destfile_path = destfile_path,
                directory = directory)
    print("Running with->", command)
    ret = subprocess.check_output(command, shell=True).decode('utf-8')
    return ret, storage_path, filename


def get_string_value_if_list(dict_like, key, separator=';'):
    value = dict_like.get(key, None)
    if isinstance(value, list):
        return separator.join(value)
    return value


def get_sorting_value(value, key, number_keys=None, default_value=''):
    '''Returns value which is used for sorting of book items.
    '''
    if value is None:
        return 0 if number_keys and key in number_keys else default_value
    return value


def convert_scandata_angle_to_thumbs_rotation(angle, scandata_rotation_angle):
    rotations = {
        0: 0,
        90: -90,
        180: 180,
        -90: 90,
        270 : 90,
    }
    return rotations[angle]

def all_files_under(path):
    """Iterates through all files that are under the given path."""
    for cur_path, dirnames, filenames in os.walk(path):
        for filename in filenames:
            yield os.path.join(cur_path, filename)


def ensure_book_directory(book_path):
    thumb_path = os.path.join(book_path, 'thumbnails')
    if not os.path.exists(thumb_path):
        os.makedirs(thumb_path)
        Logger.info('Book: Created book directory at: {}'.format(book_path))


def create_mesh_vertices(pos, size, uvs):
    return [
        pos[0], pos[1], uvs[0], uvs[1],
        pos[0] + size[0], pos[1], uvs[2], uvs[3],
        pos[0] + size[0], pos[1] + size[1], uvs[4], uvs[5],
        pos[0], pos[1] + size[1], uvs[6], uvs[7]
    ]

def get_gravatar_url(email, size=100, default='identicon', rating='g'):
    url = 'https://secure.gravatar.com/avatar'
    hash = hashlib.md5(email.encode('utf-8')).hexdigest()
    return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(url=url,
                                                                 hash=hash,
                                                                 size=size,
                                                                 default=default,
                                                                 rating=rating)


def cradle_closed():
    DEVICE_NAME = config.get('contact_switch', None)
    if DEVICE_NAME in ['', None]:
        return True
    try:
        s = serial.Serial(port=DEVICE_NAME)
        print('Opened device {}: {} | CTS -> {}'.format(DEVICE_NAME, s, s.cts))
        return s.cts
    except Exception as e:
        print('Error {} opening device {}. Falling back open'.format(e, DEVICE_NAME))
        return False


def get_scanner_property(property):
    return get_metadata(scribe_globals.CONFIG_DIR).get(property, None)
