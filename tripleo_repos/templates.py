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


CEPH_REPO_TEMPLATE = '''
[tripleo-centos-ceph-%(ceph_release)s]
name=tripleo-centos-ceph-%(ceph_release)s
baseurl=%(mirror)s/centos/%(centos_release)s/storage/$basearch/ceph-%(ceph_release)s/
gpgcheck=0
enabled=1
'''

OPSTOOLS_REPO_TEMPLATE = '''
[tripleo-centos-opstools]
name=tripleo-centos-opstools
baseurl=%(mirror)s/centos/7/opstools/$basearch/
gpgcheck=0
enabled=1
'''

# centos-8 only
HIGHAVAILABILITY_REPO_TEMPLATE = '''
[tripleo-centos-highavailability]
name=tripleo-centos-highavailability
baseurl=%(mirror)s/centos/%(stream)s/HighAvailability/$basearch/os/
gpgcheck=0
enabled=1
'''

# centos-8 only
POWERTOOLS_REPO_TEMPLATE = '''
[tripleo-centos-powertools]
name=tripleo-centos-powertools
baseurl=%(mirror)s/centos/%(stream)s/PowerTools/$basearch/os/
gpgcheck=0
enabled=1
'''

# ubi-8 only
APPSTREAM_REPO_TEMPLATE = '''
[AppStream]
name=CentOS-$releasever - AppStream
baseurl=%(mirror)s/centos/$releasever/AppStream/$basearch/os/
gpgcheck=0
enabled=1
%(extra)s
'''

BASE_REPO_TEMPLATE = '''
[BaseOS]
name=CentOS-$releasever - Base
baseurl=%(mirror)s/centos/$releasever/BaseOS/$basearch/os/
gpgcheck=0
enabled=1
'''
