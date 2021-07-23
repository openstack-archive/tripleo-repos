#   Copyright 2021 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.
#
#
from __future__ import (absolute_import, division, print_function)
"""
List of options that can be updated for yum repo files.
"""

__metaclass__ = type
YUM_REPO_SUPPORTED_OPTIONS = [
    'name',
    'baseurl',
    'enabled',
    'gpgcheck',
    'gpgkey',
    'priority',
    'exclude',
]

"""
Default constants for yum repo operations.
"""
YUM_REPO_DIR = '/etc/yum.repos.d'
YUM_REPO_FILE_EXTENSION = '.repo'

"""
Default constants for yum/dnf global configurations.
"""
YUM_GLOBAL_CONFIG_FILE_PATH = '/etc/yum.conf'
