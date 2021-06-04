#!/usr/bin/env python

# Copyright 2016 Red Hat, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re


# Regexes
TITLE_RE = re.compile('\\[(.*)\\]')
NAME_RE = re.compile('name=(.+)')
PRIORITY_RE = re.compile('priority=\\d+')


# Packages to be included from delorean-current when using current-tripleo
INCLUDE_PKGS = ('includepkgs=instack,instack-undercloud,'
                'os-apply-config,os-collect-config,os-net-config,'
                'os-refresh-config,python*-tripleoclient,'
                'openstack-tripleo-*,openstack-puppet-modules,'
                'ansible-role-tripleo*,puppet-*,python*-tripleo-common,'
                'python*-paunch*,tripleo-ansible,ansible-config_template')

# RHEL is only provided to licensed cloud providers via RHUI
DEFAULT_MIRROR_MAP = {
    'fedora': 'https://mirrors.fedoraproject.org',
    'centos': 'http://mirror.centos.org',
    'ubi': 'http://mirror.centos.org',
    'rhel': 'https://trunk.rdoproject.org',
}

# unversioned fedora added for backwards compatibility
SUPPORTED_DISTROS = [
    ('centos', '7'),
    ('centos', '8'),
    ('fedora', ''),
    ('rhel', '8'),
    ('ubi', '8')  # a subcase of the rhel distro
]

DEFAULT_OUTPUT_PATH = '/etc/yum.repos.d'
DEFAULT_RDO_MIRROR = 'https://trunk.rdoproject.org'
