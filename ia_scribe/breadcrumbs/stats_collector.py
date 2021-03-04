import time, os, datetime
from ia_scribe.database.database import Database
from ia_scribe.scribe_globals import (STATS_DIR,
                                      STATS_FILENAME_BUCKET_FORMAT,
                                      STATS_FILENAME_FORMAT,
                                      EVENTS_SCHEMA,)
from ia_scribe.config.config import Scribe3Configuration

config = Scribe3Configuration()


def get_db_filename():
    current_bucket = datetime.datetime.now().strftime(STATS_FILENAME_BUCKET_FORMAT)
    filename = STATS_FILENAME_FORMAT.format(current_bucket)
    ret = os.path.join(STATS_DIR, filename)
    return ret


db = Database(filename=get_db_filename(),
              name='Stats collector',
              schema=EVENTS_SCHEMA)

if not config.is_true('stats_disabled'):
    db.start()


def _log_event(component, metric, value, facet=None):
    t = time.time()
    operator = config.get('operator')
    db.insert('events', (t,
                         operator,
                         component,
                         metric,
                         value,
                         facet))




