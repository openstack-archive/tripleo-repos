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

import sys

from cliff.app import App
from cliff.commandmanager import CommandManager


class TripleoReposApp(App):

    def __init__(self):
        super(TripleoReposApp, self).__init__(
            description='Tripleo repos tool',
            version='2.0',
            command_manager=CommandManager('tripleo_repos.cm'),
            deferred_help=True)

    def initialize_app(self, argv):
        self.LOG.debug('Initializing tripleo-repos tool')

    def prepare_to_run_command(self, cmd):
        self.LOG.debug('prepare_to_run_command %s', cmd.__class__.__name__)

    def clean_up(self, cmd, result, err):
        self.LOG.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.LOG.debug('Error: %s', err)


def main(argv=sys.argv[1:]):
    tripleo_app = TripleoReposApp()

    # Hack to keep compatibility for now
    if 'generate' not in argv:
        argv.insert(0, 'generate')
    return tripleo_app.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
