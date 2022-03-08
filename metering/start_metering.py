import os
from django import setup


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gosc.settings')
setup()


if __name__ == "__main__":
    from metering.measurers import ServerMeasurer
    ServerMeasurer().run()
