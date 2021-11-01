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
    'baseurl',
    'cost',
    'enabled',
    'exclude',
    'excludepkgs',
    'gpgcheck',
    'gpgkey',
    'includepkgs',
    'metalink',
    'mirrorlist',
    'module_hotfixes',
    'name',
    'priority',
    'skip_if_unavailable',
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

"""
CentOS Stream compose repos defaults
"""
COMPOSE_REPOS_RELEASES = [
    "centos-stream-8",
    "centos-stream-9"
]

COMPOSE_REPOS_SUPPORTED_ARCHS = [
    "aarch64",
    "ppc64le",
    "x86_64"
]

COMPOSE_REPOS_URL_PATTERN = {
    "centos-stream-8": r"(^https:.*.centos.org/)([^/]*)(/compose/?$)",
    "centos-stream-9": r"(^https:.*.centos.org/.*/)(.*)(/compose/?$)",
}

COMPOSE_REPOS_URL_REPLACE_STR = {
    "centos-stream-8": r"\1%(compose_id)s\3",
    "centos-stream-9": r"\1%(compose_id)s\3",
}

COMPOSE_REPOS_INFO_PATH = {
    "centos-stream-8": "metadata/composeinfo.json",
    "centos-stream-9": "metadata/composeinfo.json",
}

"""
DNF Manager constants
"""
DNF_MODULE_MINIMAL_DISTRO_VERSIONS = [
    {'distro': 'centos', 'min_version': 8},
    {'distro': 'rhel', 'min_version': 8},
    {'distro': 'fedora', 'min_version': 22},
]
