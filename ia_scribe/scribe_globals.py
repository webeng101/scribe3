#!/usr/bin/env python
'''
Module contains the baked-in configurations for the Scribe3 software
'''

from distutils.spawn import find_executable
from os.path import join, dirname, expanduser

# Release Information
release_date = '11-03-2020'
release_version = '4.3'
release_status = 'Dev'

DEBUG = False

ENTRY_POINTS = ['main.py', 'ia-scribe']
APP_WORKING_DIR = dirname(dirname(__file__))
LIBS_DIR = join(APP_WORKING_DIR, 'libs')
ASSETS_DIR = join(APP_WORKING_DIR, 'assets')
CONFIGS_DIR = join(ASSETS_DIR, 'configs')
IMAGES_DIR = join(ASSETS_DIR, 'images')
IMAGES_SETTINGS_DIR = join(IMAGES_DIR, 'settings')
FONTS_DIR = join(ASSETS_DIR, 'fonts')
SOUNDS_DIR = join(ASSETS_DIR, 'sounds')
NOTES_DIR = join(ASSETS_DIR, 'notes')

LOADING_IMAGE = join(IMAGES_DIR, 'image-loading.gif')
FAKE_IMAGE = join(IMAGES_DIR, 'fake.jpg')
MISSING_IMAGE = join(IMAGES_DIR, 'missing.png')

DEFAULT_FONT_FILES = ['DroidSans',
                      join(FONTS_DIR, 'DroidSans.ttf'),
                      join(FONTS_DIR, 'DroidSans-Italic.ttf'),
                      join(FONTS_DIR, 'DroidSans-Bold.ttf'),
                      join(FONTS_DIR, 'DroidSans-BoldItalic.ttf')]

EXIFTOOL = find_executable('exiftool')

PRINT_LABEL_FILENAME = 'label.png'
DEFAULT_PRINTER_NAME = 'DYMO_LabelWriter_450_Turbo'

# Timeout for events push to iabdash
IABDASH_TIMEOUT = 5

HALD_FILE = join(IMAGES_DIR, 'hald8.png')

try:
    with open(join(APP_WORKING_DIR, 'build_number')) as fp:
        build_number_from_file = fp.read().strip('\n')
except Exception:
    build_number_from_file = None

BUILD_NUMBER = build_number_from_file or release_version

KAKADU_DIR = join(LIBS_DIR, 'kakadu')
KAKADU_COMPRESS = join(KAKADU_DIR, 'kdu_compress')
KAKADU_SLOPE = '42808'

# for debugging WITHOUT CAMERAS connected set fake_cameras = 2
# for debugging foldouts with three fake cameras, set fake_cameras to 3
FAKE_CAMERAS = False

# Font that can display UTF-8 glyphs for internationalization
UTF8_FONT = 'FreeSansTTScribe'

# Where the books are stored
BOOKS_DIR = join(expanduser('~'), 'scribe_books')

# the main configuration folder
CONFIG_DIR = join(expanduser('~'), '.scribe')
# add-ons configurations like the S3 keys locations
SCRIBE_CONFIG_FILE = join(CONFIG_DIR, 'scribe_config.yml')
HALD_FILE_CUSTOM = join(CONFIG_DIR, 'hald8.png')

# Database file location
STATS_BASE_DIR = join(CONFIG_DIR, 'stats')
STATS_DIR = join(STATS_BASE_DIR, 'events')
PROCESSED_STATS_DIR = join(STATS_BASE_DIR, 'processed')
METRICS_DIR = join(STATS_BASE_DIR, 'metrics')

STATS_FILENAME_BUCKET_FORMAT = '%Y_%m_%d'
STATS_FILENAME_FORMAT = 'stats_{}.db'
EVENTS_SCHEMA = {
    'events':
        [ {'name': 'time','type': 'TEXT',},
         {'name': 'operator', 'type': 'TEXT',},
         {'name': 'component', 'type': 'TEXT',},
         {'name': 'metric', 'type': 'TEXT',},
         {'name': 'value', 'type': 'TEXT',},
         {'name': 'facet', 'type': 'TEXT',},
         ],
}

RECENT_USERS_FILE = join(CONFIG_DIR, 'recent_users.json')
# Required version of capture_action_bindings.json
CAPTURE_ACTION_BINDINGS_VERSION = 8

# File which contains keyboard scancode to capture action bindings.
# End-user can edit this file.
CAPTURE_ACTION_BINDINGS = join(CONFIG_DIR, 'capture_action_bindings.json')

# Default bindings defined by developers and copied by app to
# capture_action_bindings if capture_action_bindings does not exists or
# versions do not match
DEFAULT_CAPTURE_ACTION_BINDINGS = join(CONFIGS_DIR,
                                       'capture_action_bindings.json')

# Similar to capture actions
RESHOOT_ACTION_BINDINGS_VERSION = 2
RESHOOT_ACTION_BINDINGS = join(CONFIG_DIR, 'reshoot_action_bindings.json')
DEFAULT_RESHOOT_ACTION_BINDINGS = join(CONFIGS_DIR,
                                       'reshoot_action_bindings.json')

SCANCENTER_METADATA_DIR = '~/.scribe'

LOGGING_FORMAT = '[%(asctime)s][%(levelname)-5s][%(threadName)-8s]' \
                 '[%(name)-10s] %(message)s'

FLAT_MD_FIELDS = ['isbn', 'issn']

DEFAULT_OXCART_PAYLOAD_MD_KEYS = ['scanningcenter', 'operator', 'tts_version']

DEFAULT_PPI = 300

# Image is considered blurry if it's variance is lower than this value
BLUR_VARIANCE_THRESHOLD = 200

ORIGINAL_ISBN_FILENAME = 'original_isbn.txt'

TASK_DEFAULT_MAX_RETRIES = 5

ALLOWED_DOWNLOAD_REPUB_STATES = [31, 41]

NUMBER_OF_HIPRIO_RUNNERS = 4
NUMBER_OF_NORMAL_RUNNERS = 8
NUMBER_OF_HEAVY_RUNNERS = 4

STATS_REFRESH_INTERVAL = None
RUNNER_BACKOFF = 5
SCHEDULER_GRACE_PERIOD = 5
SCHEDULER_INTERVAL = 120

SAFE_REPUB_STATES = [12, 13, 14, 15, 18, 19, 20, 21, 22, 35]

CATALOGS = {'trent': True, 'philips': True, 'sfpl': True, 'marygrove': True}
DEFAULT_CATALOG = 'trent'

LOGOUT_TIMEOUT = 300

OL_DEDUPE_URL = 'https://archive.org/book/marc/ol_dedupe.php'

ZTARGETS_URL = 'https://archive.org/book/marc/assign_marcs.php?get_catalog_list'
ZTARGETS_FILENAME = 'ztargets.json'
ZTARGETS_FULL_PATH = join(CONFIG_DIR, ZTARGETS_FILENAME)
ZFETCH_URL = 'https://archive.org/book/marc/zfetch.php?catalog={catalog}&query={query}'

C2_REGISTRATION_API = 'https://iabooks.archive.org/c2_register'

C2_SERVER = 'books-c2.us.archive.org'
C2_SERVER_PORT = 7777

RCS_API_URL = 'https://archive.org/book/metadata/rcs.php'
REMOTE_RCS_FILE = join(CONFIG_DIR, 'remote_rcs.json')
LOCAL_RCS_FILE = join(CONFIG_DIR, 'local_rcs.json')

PICKLE_PROTOCOL = 2

SUPERCENTERS = ['cebu', 'sanfrancisco', 'sheridan', ]
