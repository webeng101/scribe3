import yaml
import os
from pprint import pformat

from kivy.logger import Logger
from ia_scribe import scribe_globals
from ia_scribe.exceptions import ScribeException, CredentialsError
from ia_scribe.abstract import singleton

ALPHANUMERIC_FIELDS = ['printer',]
NUMBERS_ONLY_FIELDS = ['runners_hiprio', 'camera_ppi', 'defer_delete_by',
                       'periodic_move_along_interval', 'runners_general_purpose', 'runners_slow_task',
                       'stats_polling_interval', 'scheduler_interval', 'upload_threads']

@singleton
class Scribe3Configuration(object):

    configuration = {}

    def __init__(self, config_file=scribe_globals.SCRIBE_CONFIG_FILE):
        self.observers = []
        self.config_file_path = config_file
        self._load_config()

    def __contains__(self, item):
        return item in self.configuration

    def _load_config(self):
        Logger.info('Config initialization: Begin')
        self._ensure_file_exists()
        configuration = self._read()
        if self.is_valid(configuration):
            self.configuration = configuration

    def subscribe(self, observer):
        if observer not in self.observers:
            self.observers.append(observer)

    def unsubcribe(self, observer):
        if observer in self.observers:
            self.observers.remove(observer)

    def notify(self, event_type, payload,):
        for observer in self.observers[:]:
            observer(event_type, payload)

    def dump(self):
        return self.configuration

    def get(self, key, if_none=None):
        base_key = key
        offset_key = None
        if '/' in key:
            base_key, offset_key = key.split('/')

        res = query_result = self.configuration.get(base_key, if_none)

        if offset_key and query_result is not None:
            res = query_result[offset_key]

        return res

    def get_numeric_or_none(self, key, type=int):
        result = self.get(key)
        try:
            res = type(result)
            return res
        except Exception as e:
            return None

    def get_integer(self, key, return_if_none=None):
        result = self.get(key)
        try:
            res = int(result)
            if res is None:
                return return_if_none
            else:
                return res
        except Exception as e:
            return return_if_none

    def get_field_validator(self, key):
        numbers_only = '[1-9][0-9]*'
        alphanumeric = '\w+'
        if key in ALPHANUMERIC_FIELDS:
            return alphanumeric
        elif key in NUMBERS_ONLY_FIELDS:
            return numbers_only
        else:
            return None

    def set(self, key, value):
        self._update_key(self.configuration, key, value)
        self._save()
        self.notify('key_set', (key, value), )

    def has_key(self, key):
        return self.get(key) is not None

    def is_true(self, key):
        return self.get(key) in ['True', True, 'true']

    def _read(self):
        try:
            with open(self.config_file_path) as f:
                read_from_file = yaml.safe_load(f)
                if read_from_file:
                    return read_from_file
                else:
                    return None
        except Exception as e:
            raise Exception('Could not read {}: {}'.format(scribe_globals.SCRIBE_CONFIG_FILE, e))

    def _save(self):
        try:
            with open(self.config_file_path, 'w+') as f:
                yaml.safe_dump(self.configuration, f, default_flow_style=False)
            Logger.debug('Scribe3Configuration: Saved:\n{}'
                        .format(pformat(self.configuration)))
        except Exception:
            raise ScribeException('Could not save config to {}'
                                  .format(self.config_file_path))

    def _update_key(self, node, key, val):
        parts = key.split('/')
        for part in parts[:-1]:
            if part not in node:
                node[part] = {}
            node = node[part]
        node[parts[-1]] = val
        return node

    def _get(self, node, key):
        parts = key.split('/')
        for part in parts:
            if part not in node:
                return None
            node = node[part]
        return node

    def _ensure_file_exists(self):
        if not os.path.exists(self.config_file_path):
            config_dir = scribe_globals.CONFIG_DIR
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            if not os.access(config_dir, os.W_OK | os.X_OK):
                raise ScribeException('Config dir "{}" not writable'
                                      .format(config_dir))
            os.mknod(self.config_file_path)
        if os.stat(self.config_file_path).st_size == 0:
            self._initialize()

    def _validate(self, candidate_config):
        try:
            return self.validate(candidate_config)
        except Exception as e:
            #return False
            print(e)
            pass

    def is_valid(self, configuration):
        if configuration == {}:
            return True
        try:
            self.validate(configuration)
            return True
        except:
            return False

    def validate(self, config=None):
        if config is None:
            config = self.configuration
        if 's3' not in config:
            raise CredentialsError('You are logged out. Please login from '
                                 'the "Account" options screen.')

        if 'access_key' not in config['s3']:
            raise CredentialsError('IAS3 Access Key not in scribe3 configuration file')

        if 'secret_key' not in config['s3']:
            raise CredentialsError('IAS3 Secret Key not in scribe3 configuration file')

        if 'cookie' not in config:
            raise CredentialsError('The cookie is not present.')

        return True

    def _initialize(self):
        config = self.configuration
        if 'printer' not in config:
            Logger.info('Config initialization: Printer not found in config. '
                        'Setting default = DYMO_LabelWriter_450_Turbo ')

            self.set('printer', 'HLL2300D')
        # check if camera logging is enabled
        if 'camera_logging' not in config:
            Logger.info('Config initialization: '
                        'Camera logging is not activated.')

        if 'runners_hiprio' not in config:
            Logger.info('Config initialization: '
                        'High priority runners # not specified, defaulting to {}'.format
                (scribe_globals.NUMBER_OF_HIPRIO_RUNNERS))
            self.set('runners_hiprio', scribe_globals.NUMBER_OF_HIPRIO_RUNNERS)

        if 'runners_general_purpose' not in config:
            Logger.info('Config initialization: '
                        'General purpose runners # not specified, defaulting to {}'.format
                (scribe_globals.NUMBER_OF_NORMAL_RUNNERS))
            self.set( 'runners_general_purpose', scribe_globals.NUMBER_OF_NORMAL_RUNNERS)

        if 'runners_slow_task' not in config:
            Logger.info('Config initialization: '
                        'Slow task runners # not specified, defaulting to {}'.format
                (scribe_globals.NUMBER_OF_HEAVY_RUNNERS))
            self.set('runners_slow_task', scribe_globals.NUMBER_OF_HEAVY_RUNNERS)

        if 'scheduler_interval' not in config:
            Logger.info('Config initialization: '
                        'Scheduler interval is not specified, defaulting to {}s'.format(scribe_globals.SCHEDULER_INTERVAL))
            self.set('scheduler_interval', scribe_globals.SCHEDULER_INTERVAL)

        if 'stats_polling_interval' not in config:
            Logger.info('Config initialization: '
                        'Stats polling interval not specified, defaulting to {}s')
            self.set('stats_polling_interval', scribe_globals.STATS_REFRESH_INTERVAL)

        if 'default_single_camera_rotation' not in config:
            Logger.info('Config initialization: '
                        'default_single_camera_rotation not specified, defaulting to 1.')
            self.set('default_single_camera_rotation', 180)

        if 'compression_threads' not in config:
            Logger.info('Config initialization: '
                        'Compression threads not specified, defaulting to 1.')
            self.set('compression_threads', 1)

        if 'camera_ppi' not in config:
            default_ppi = '360'
            Logger.info('Config initialization: '
                        'Default camera PPI value not found')
            self.set('camera_ppi', default_ppi)
            Logger.info('Config initialization: Set default camera PPI value '
                        'to {}'.format(default_ppi))

        if 'postprocess_instructions' not in config:
            Logger.info('Config initialization: postprocessing options')
            fadgi_options = {
                'skipContrastEnhancement': False,
                'correctToneColor': False,
                'attachIccProfile': False,
            }
            self.set('postprocess_instructions', fadgi_options)
            Logger.info('Config initialization: Set default postprocessing options'
                        'to {}'.format(fadgi_options))

        if 'set_noindex' not in config:
            set_noindex_value = True
            Logger.info('Config initialization: '
                        'No option specified for set_noindex, assuming TRUE!'
                        'To upload your items as searchable, turn this off from Settings -> General')
            self.set('set_noindex', set_noindex_value)
            Logger.info('Config initialization: Set set_noindex value '
                        'to {}'.format(set_noindex_value))

        if 'skip_blur_detection' not in config:
            skip_blur_detection = True
            Logger.info('Config initialization: '
                        'No option specified for skip_blur_detection, assuming TRUE!'
                        'To enable blur detect, turn this off in settings')
            self.set('skip_blur_detection', skip_blur_detection)
            Logger.info('Config initialization: Set set_noindex value '
                        'to {}'.format(skip_blur_detection))

        if 'periodic_move_along_interval' not in config:
            Logger.info('Config initialization: '
                        'Periodic move along interval not found, setting to 300 seconds.')
            self.set('periodic_move_along_interval', 300)

        if 'notification_cleanup_interval' not in config:
            Logger.info('Config initialization: '
                        'Notifications cleanup interval not found, setting to 60 seconds')
            self.set('notification_cleanup_interval', 60)

        if 'move_along_at_startup' not in config:
            Logger.info('Config initialization: '
                        'Enabling move along at startup.')
            self.set('move_along_at_startup', True)

        if 'wonderfetch_validation_regex' not in config:
            wonderfetch_validation_regex = '\d+'
            Logger.info('Config initialization: '
                        'No option specified for wonderfetch_validation_regex, assuming: {}'.format
                (wonderfetch_validation_regex))
            self.set('wonderfetch_validation_regex', wonderfetch_validation_regex)
            Logger.info('Config initialization: Set wonderfetch_validation_regex value '
                        'to {}'.format(wonderfetch_validation_regex))

        if 'defer_delete_by' not in config:
            defer_delete_by = 1
            Logger.info('Config initialization: '
                        'Default deferred deletion policy not set.')
            self.set('defer_delete_by',
                                 defer_delete_by)
            Logger.info('Config initialization: Set default deferred deletion policy'
                        'to {} hours'.format(defer_delete_by))

        if 'catalogs' not in config:
            catalogs =  scribe_globals.CATALOGS
            Logger.info('Config initialization: '
                        'Wonderfetch catalogs not set.')
            self.set('catalogs', catalogs)
            Logger.info('Config initialization: Set wonderfetch catalogs'
                        'to {}'.format(catalogs))

        if 'default_catalog' not in config:
            default_catalog =  scribe_globals.DEFAULT_CATALOG
            Logger.info('Config initialization: '
                        'Default wonderfetch catalog not set.')
            self.set('catalogs', catalogs)
            Logger.info('Config initialization: Set default wonderfetch catalog'
                        'to {}'.format(default_catalog))

        if 'c2_server' not in config:
            default_value = scribe_globals.C2_SERVER
            self.set('c2_server', default_value)

        Logger.info('Config initialization: '
                    'Read the following settings -> [{}]'.format(', '.join(config.keys())))
