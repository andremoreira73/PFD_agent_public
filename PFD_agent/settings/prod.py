#######################################
## VM / production settings 
#######################################

import os
from .base import *



# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False  #VM

CSRF_TRUSTED_ORIGINS = [
    'https://pfd-agent.lyfx.ai',
    'http://pfd-agent.lyfx.ai',  # Include HTTP version too, just in case
]

ALLOWED_HOSTS = [
    'pfd-agent.lyfx.ai',
    'localhost',
    '127.0.0.1',
]


# Browser reload (development)
if DEBUG:
    INTERNAL_IPS = [
        "127.0.0.1",
    ]