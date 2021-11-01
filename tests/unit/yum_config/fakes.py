#   Copyright 2021 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

FAKE_FILE_PATH = '/path/to/file'
FAKE_DIR_PATH = '/path/to/dir'
FAKE_SUPP_OPTIONS = ['fake_option1', 'fake_option2']
FAKE_OPTION1 = 'fake_option1'
FAKE_DIR_FILES = ['fake_file1.conf', 'fake_file2.conf', 'fake.md']
FAKE_SECTIONS = ['fake_section1', 'fake_section2']
FAKE_SECTION1 = 'fake_section1'
FAKE_SECTION2 = 'fake_section2'
FAKE_SET_DICT = {
    'key1': 'value1',
    'key2': 'value2',
}
FAKE_REPO_DOWN_URL = '/fake/down/url/fake.repo'

FAKE_COMPOSE_URL = (
    'https://composes.centos.org/fake-CentOS-Stream/compose/')
FAKE_REPO_PATH = '/etc/yum.repos.d/fake.repo'
FAKE_RELEASE_NAME = 'fake_release'

FAKE_COMPOSE_INFO = {
    "header": {
        "version": "1.2",
    },
    "payload": {
        "compose": {
            "id": "fake_compose_id",
        },
        "release": {
            "name": "CentOS Stream",
            "short": "CentOS-Stream",
            "version": "8",
        },
        "variants": {
            "AppStream": {
                "arches": [
                    "aarch64",
                    "ppc64le",
                    "x86_64"
                ],
                "id": "AppStream",
                "name": "AppStream",
                "paths": {
                    "packages": {
                        "aarch64": "AppStream/aarch64/os/Packages",
                        "ppc64le": "AppStream/ppc64le/os/Packages",
                        "x86_64": "AppStream/x86_64/os/Packages",
                    },
                },
            },
            "BaseOS": {
                "arches": [
                    "aarch64",
                    "ppc64le",
                    "x86_64",
                ],
                "id": "BaseOS",
                "name": "BaseOS",
                "paths": {
                    "packages": {
                        "aarch64": "BaseOS/aarch64/os/Packages",
                        "ppc64le": "BaseOS/ppc64le/os/Packages",
                        "x86_64": "BaseOS/x86_64/os/Packages",
                    },
                },
            },
        },
    },
}

FAKE_ENV_OUTPUT = """
LANG=C.utf8
HOSTNAME=4cb7d7db1907
which_declare=declare -f
container=oci
PWD=/
HOME=/root
TERM=xterm
SHLVL=1
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
_=/usr/bin/env
"""


class FakeConfigParser(dict):
    def __init__(self, *args, **kwargs):
        super(FakeConfigParser, self).__init__(*args, **kwargs)
        self.__dict__ = self

    def write(self, file, space_around_delimiters=False):
        pass

    def read(self, file):
        pass

    def add_section(self, section):
        self[section] = {}

    def sections(self):
        return self.keys()
