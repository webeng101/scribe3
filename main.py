import argparse
import sys
import time
import traceback

def run_cli(*args, **kwargs):
    from cli import cli
    cli.entry_point(*args, **kwargs)

def run_gui(*args,**kwargs):
    from ia_scribe.ia_services.tts import raven_client
    from kivy.logger import Logger
    from ia_scribe.scribe_app import Scribe3App
    try:
        app = Scribe3App()
        app.run()
        while app.needs_restart:
            Logger.info('App: Restarting app')
            app = Scribe3App()
            app.run()
    except KeyboardInterrupt:
        traceback.print_exc()
    except Exception:
        print('Scribe3 app experienced a boot time error')
        traceback.print_exc()
        raven_client.captureException(exc_info=sys.exc_info())
        time.sleep(3)

def run_headless(*args, **kwargs):
    from ia_scribe.headless.main import HeadlessScribe3
    app = HeadlessScribe3()
    app.run()

if __name__ == '__main__':
    # Configure argparser
    parser = argparse.ArgumentParser(description='Scribe3')
    parser.add_argument('--mode', '-m', default=None, type=str,
                        help="Mode (cli, gui)")
    args, unknown = parser.parse_known_args()
    sys.argv[1:] = unknown

    mode = args.mode or 'gui'
    downstream_args = sys.argv[1:]

    if mode == 'cli':
        run_cli()
    elif mode == 'headless':
        run_headless()
    else:
        run_gui(downstream_args)
