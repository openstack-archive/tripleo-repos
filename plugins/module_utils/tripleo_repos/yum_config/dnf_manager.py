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
import logging


__metaclass__ = type


class DnfModuleManager:
    """Class that manages dnf modules."""

    def __init__(self):
        # lazy import to allow CLI to start without dnf
        import dnf
        self.base = dnf.Base()
        self.base.conf.read()
        self.base.conf.best = True
        self.base.read_all_repos()
        self.base.fill_sack()
        self.module_base = dnf.module.module_base.ModuleBase(self.base)

    def _get_module_spec(self, name, stream=None, profile=None):
        """Return a module spec string based on stream and/or profile."""
        module_spec = name
        if stream:
            module_spec += ':{0}'.format(stream)
        if profile:
            module_spec += '/{0}'.format(profile)
        return module_spec

    def _do_transaction(self):
        """Perform the resolved transaction."""
        try:
            self.base.do_transaction()
        except RuntimeError:
            logging.error('This command has to be run with superuser '
                          'privileges.')
            raise

    def enable_module(self, name, stream=None, profile=None):
        """Enable a module stream."""
        self.module_base.enable(
            [self._get_module_spec(name, stream=stream, profile=profile)]
        )
        self._do_transaction()
        logging.info("Module %s was enabled.", name)

    def disable_module(self, name, stream=None, profile=None):
        """Disable a module stream."""
        self.module_base.disable(
            [self._get_module_spec(name, stream=stream, profile=profile)]
        )
        self._do_transaction()
        logging.info("Module %s was disabled.", name)

    def reset_module(self, name, stream=None, profile=None):
        """Reset a module. It will no longer be enabled or disabled."""
        self.module_base.reset(
            [self._get_module_spec(name, stream=stream, profile=profile)]
        )
        self._do_transaction()
        logging.info("Module %s was reset.", name)

    def install_module(self, name, stream=None, profile=None):
        """Install packages of a module profile."""
        self.module_base.install(
            [self._get_module_spec(name, stream=stream, profile=profile)]
        )
        self.base.resolve()
        self.base.download_packages(self.base.transaction.install_set)
        self._do_transaction()
        logging.info("Module %s was installed.", name)

    def remove_module(self, name, stream=None, profile=None):
        """Remove packages of a module profile."""
        self.module_base.remove(
            [self._get_module_spec(name, stream=stream, profile=profile)]
        )
        self._do_transaction()
        logging.info("Module %s was removed.", name)
