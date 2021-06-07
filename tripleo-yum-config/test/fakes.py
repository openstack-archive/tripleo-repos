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


class FakeConfigParser(dict):
    def __init__(self, *args, **kwargs):
        super(FakeConfigParser, self).__init__(*args, **kwargs)
        self.__dict__ = self

    def write(self, file):
        pass

    def read(self, file):
        pass

    def add_section(self, section):
        pass
