import sys
import os
import socket
import asyncio
import argparse
import logging
import configparser

from hpxclient import settings

from hpxclient.mng import service as mng_service
from hpxclient.fetcher.central import service as fetcher_central_service


logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)7s: %(message)s',
    stream=sys.stdout,
)

def set_ips(settings, domain):
    ip_consts = ['LISTENER', 'FETCHER', 'MNG', 'BRIDGE']
    domain_ip = socket.gethostbyname(domain)

    for ip_const in ip_consts:
        setting_name = 'PROXY_%s_SERVER_IP' % ip_const
        setattr(settings, setting_name, domain_ip)
    setattr(settings, 'DOMAIN_IP', domain_ip)


def load_data_config_file(config_file):
    if not config_file:
        config_file = os.path.join(settings.HPROX_DIR,
                                   settings.HPROX_CONFIG_NAME)

    config = configparser.ConfigParser()
    try:
        config.read_file(open(config_file))
    except FileNotFoundError:
        print("No file settings found: %s", config_file)

    _NOT_ALLOWED_IN_CONF = ["SECRET_KEY", ]
    _INVALID_PARAM_ERROR = "Not valid configuration parameter: %s"

    for section in config.sections():
        for name, value in config[section].items():
            try:
                getattr(settings, name.upper())
            except AttributeError:
                print(_INVALID_PARAM_ERROR % name)

            if 'DOMAIN' in name.upper():
                set_ips(settings, value)

            if name.upper() in _NOT_ALLOWED_IN_CONF:
                raise argparse.ArgumentTypeError(_INVALID_PARAM_ERROR % name)
            setattr(settings, name.upper(), value)

    if hasattr(settings, 'SECRET_KEY_FILE') and settings.SECRET_KEY_FILE:
        try:
            with open(settings.SECRET_KEY_FILE) as f:
                settings.SECRET_KEY = f.readline().strip()
        except FileNotFoundError:
            raise Exception("No secret key file found: %s" %settings.SECRET_KEY_FILE)


def load_config():
    """ Load configuration settings from hprox.cfg. If any
    extra parameter is supplied via command overwrites the
    configuration file.

    We consider as a valid configuration setting all items
    listed in the hpxclient.consts.
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", type=int, choices=[0, 1, 2],
                        help="increase output verbosity")

    parser.add_argument("-pk", "--public-key",
                        dest="PUBLIC_KEY",
                        help="Define the network's access PUBLIC KEY.")

    parser.add_argument("-skf", "--secret-key-file",
                        dest="SECRET_KEY_FILE",
                        help="Define the file that contains the network's access SECRET KEY.")

    parser.add_argument("-c", "--config",
                        dest="config_file",
                        help="Define configuration file.")

    args = parser.parse_args()
    config_file = args.config_file
    load_data_config_file(config_file)

    # Loading settings from the command line. They overwrite config file.
    for name, value in vars(args).items():
        if not value:
            continue
        setattr(settings, name, value)

    # Loading settings from environ. They overwrite everything.
    if "HPROX_PUBLIC_KEY" in os.environ:
        print("Reading PUBLIC KEY from environment.")
        settings.PUBLIC_KEY = os.environ["HPROX_PUBLIC_KEY"]

    if "HPROX_SECRET_KEY" in os.environ:
        print("Reading SECRET KEY from environment.")
        settings.SECRET_KEY = os.environ["HPROX_SECRET_KEY"]


def run_daemon():
    load_config()
    loop = asyncio.get_event_loop()
    loop.set_debug(True)

    loop.run_until_complete(asyncio.gather(
        mng_service.start_client(
            public_key=settings.PUBLIC_KEY,
            secret_key=settings.SECRET_KEY
        ),
        fetcher_central_service.start_client(
            public_key=settings.PUBLIC_KEY,
            secret_key=settings.SECRET_KEY
        )
    ))

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        sys.stderr.flush()
        print('\nClient stopped\n')

    finally:
        pending = asyncio.Task.all_tasks()
        for p in pending:
            p.cancel()
        loop.run_until_complete(loop.shutdown_asyncgens())


if __name__ == "__main__":
    run_daemon()
