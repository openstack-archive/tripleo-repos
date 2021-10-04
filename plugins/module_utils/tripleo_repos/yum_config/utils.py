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
from __future__ import (absolute_import, division, print_function)
import os
import platform
import subprocess

__metaclass__ = type


# TODO(dviroel): Merge in a utils file when refactoring tripleo-repos.
def get_distro_info():
    """Get distro info from os-release file.

    :return: distro_id, distro_major_version_id and distro_name
    """
    if not os.path.exists('/etc/os-release'):
        return platform.system(), 'unknown', 'unknown'

    output = subprocess.Popen(
        'source /etc/os-release && echo -e -n "$ID\n$VERSION_ID\n$NAME"',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=open(os.devnull, 'w'),
        executable='/bin/bash',
        universal_newlines=True).communicate()

    # distro_id and distro_version_id will always be at least an empty string
    distro_id, distro_version_id, distro_name = output[0].split('\n')

    # if distro_version_id is empty string the major version will be empty
    # string too
    distro_major_version_id = distro_version_id.split('.')[0]

    # check if that is UBI subcase?
    if os.path.exists('/etc/yum.repos.d/ubi.repo'):
        distro_id = 'ubi'

    return distro_id, distro_major_version_id, distro_name
