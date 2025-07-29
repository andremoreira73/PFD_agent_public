#######################################
## local settings 
#######################################

import os
from .base import *




# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '*']


# Browser reload (development)
if DEBUG:
    INTERNAL_IPS = [
        "127.0.0.1",
    ]