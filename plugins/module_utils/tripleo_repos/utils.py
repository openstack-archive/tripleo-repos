#  Copyright 2021 Red Hat, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.
#
from __future__ import (absolute_import, division, print_function)

import logging
import sys

__metaclass__ = type

# portable http_get that uses either ansible recommended way or python native
# urllib. Also deals with python2 vs python3 for centos7 train jobs.
py_version = sys.version_info.major
if py_version < 3:
    import urllib2

    def http_get(url):
        try:
            response = urllib2.urlopen(url)
            return (
                response.read().decode('utf-8'),
                int(response.code))
        except Exception as e:
            return (str(e), -1)
else:
    try:
        from ansible.module_utils.urls import open_url

        def http_get(url):
            try:
                response = open_url(url, method='GET')
                return (response.read().decode('utf-8'), response.status)
            except Exception as e:
                return (str(e), -1)
    except ImportError:
        from urllib.request import urlopen

        def http_get(url):
            try:
                response = urlopen(url)
                return (
                    response.read().decode('utf-8'),
                    int(response.status))
            except Exception as e:
                return (str(e), -1)


def load_logging(level=logging.INFO, module_name="tripleo-repos"):
    """Load and set logging level. Default is set to logging.INFO level."""
    logger = logging.getLogger()
    # Only add logger once to avoid duplicated streams in tests
    if not logger.handlers:
        stdout_handlers = [
            _handler
            for _handler in logger.handlers
            if
            (
                hasattr(_handler, 'stream') and 'stdout' in
                _handler.stream.name
            )
        ]
        if stdout_handlers == []:
            formatter = logging.Formatter(
                (
                    "%(asctime)s - " + module_name + " - %(levelname)s - "
                    "%(message)s"
                )
            )
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(formatter)
            logger.addHandler(handler)
    logger.setLevel(level)
