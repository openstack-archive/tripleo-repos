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
import json
import os
import re

from .constants import (
    YUM_REPO_DIR,
    YUM_REPO_FILE_EXTENSION,
    YUM_REPO_SUPPORTED_OPTIONS,
    COMPOSE_REPOS_RELEASES,
    COMPOSE_REPOS_INFO_PATH,
    COMPOSE_REPOS_URL_PATTERN,
    COMPOSE_REPOS_URL_REPLACE_STR,
)
from .exceptions import (
    TripleOYumConfigInvalidSection,
    TripleOYumConfigComposeError,
)
from .yum_config import (
    TripleOYumConfig
)

__metaclass__ = type


class TripleOYumComposeRepoConfig(TripleOYumConfig):
    """Manages yum repo configuration files for CentOS Compose."""

    def __init__(self, compose_url, release, dir_path=None, arch=None,
                 environment_file=None):
        conf_dir_path = dir_path or YUM_REPO_DIR
        self.arch = arch or 'x86_64'

        # 1. validate release name
        if release not in COMPOSE_REPOS_RELEASES:
            msg = 'CentOS release not supported.'
            raise TripleOYumConfigComposeError(error_msg=msg)
        self.release = release

        # 2. Validate URL
        pattern = re.compile(COMPOSE_REPOS_URL_PATTERN[self.release])
        if not pattern.match(compose_url):
            msg = 'The provided URL does not match the expect pattern.'
            raise TripleOYumConfigComposeError(error_msg=msg)

        # 3. Get compose info from url
        segments = [compose_url,
                    COMPOSE_REPOS_INFO_PATH[self.release]]
        self.compose_info_url = '/'.join(s.strip('/') for s in segments)
        self.compose_info = self._get_compose_info()

        # 4. Get compose-id from metadata
        self.compose_id = self.compose_info['compose']['id']

        # 5. Replace the compose-id from url to avoid 'labels'
        repl_args = {'compose_id': self.compose_id}
        self.compose_url = (
            pattern.sub(
                COMPOSE_REPOS_URL_REPLACE_STR[self.release] % repl_args,
                compose_url)
        )

        super(TripleOYumComposeRepoConfig, self).__init__(
            valid_options=YUM_REPO_SUPPORTED_OPTIONS,
            dir_path=conf_dir_path,
            file_extension=YUM_REPO_FILE_EXTENSION,
            environment_file=environment_file)

    def _get_compose_info(self):
        """Retrieve compose info for a provided compose-id url."""
        # NOTE(dviroel): works for both centos 8 and 9
        import urllib.request
        try:
            logging.debug("Retrieving compose info from url: %s",
                          self.compose_info_url)
            res = urllib.request.urlopen(self.compose_info_url)
        except Exception:
            msg = ("Failed to retrieve compose info from url: %s"
                   % self.compose_info_url)
            raise TripleOYumConfigComposeError(error_msg=msg)
        compose_info = json.loads(res.read())
        if compose_info['header']['version'] != "1.2":
            # NOTE(dviroel): Log a warning just in case we receive a different
            #  version here. Code may fail depending on the change.
            logging.warning("Expecting compose info version '1.2' but got %s.",
                            compose_info['header']['version'])
        return compose_info['payload']

    def _get_repo_name(self, variant):
        return " ".join([self.compose_id, variant])

    def _get_repo_filename(self, variant):
        return "-".join([self.compose_id, variant]) + '.repo'

    def _get_repo_base_url(self, variant):
        """Build the base_url based on variant name and system architecture."""
        variant_info = self.compose_info['variants'][variant]
        if not variant_info['paths'].get('repository', {}).get(self.arch):
            # Variant has no support yet
            return None
        segments = [self.compose_url,
                    variant_info['paths']['repository'][self.arch]]
        return '/'.join(s.strip('/') for s in segments)

    def get_compose_variants(self):
        return self.compose_info['variants'].keys()

    def enable_compose_repos(self, variants=None, override_repos=False):
        """Enable CentOS compose repos of a given variant list.

        This function will build from scratch all repos for a given compose-id
        url. If a list of variants is not provided, it will enable all for all
        variants returned from compose info.

        :param variants: A list of variant names to be enabled.
        :param override_repos: True if all matching variants in the same
            repo directory should be disable in favor of the new repos.
        """
        if variants:
            for var in variants:
                if not (var in self.compose_info['variants'].keys()):
                    msg = 'One or more provided variants are invalid.'
                    raise TripleOYumConfigComposeError(error_msg=msg)

        else:
            variants = self.compose_info['variants'].keys()

        updated_repos = {}
        for var in variants:
            base_url = self._get_repo_base_url(var)
            if not base_url:
                continue
            add_dict = {
                'name': self._get_repo_name(var),
                'baseurl': base_url,
                'enabled': '1',
                'gpgcheck': '0',
            }
            filename = self._get_repo_filename(var)
            file_path = os.path.join(self.dir_path, filename)
            # create a file if doesn't exist and add a section to it
            try:
                self.add_section(var.lower(), add_dict, file_path)
            except TripleOYumConfigInvalidSection:
                logging.debug("Section '%s' that already exists in this file. "
                              "Trying to update it...", var)
                self.update_section(var.lower(),
                                    set_dict=add_dict,
                                    file_path=file_path)
            # needed to override other repos
            updated_repos[var.lower()] = file_path

        if override_repos:
            for var in updated_repos:
                config_files = self._get_config_files(var)
                for file in config_files:
                    if file != updated_repos[var]:
                        msg = ("Disabling matching section '%(section)s' in "
                               "configuration file: %(file)s.")
                        msg_args = {
                            'section': var,
                            'file': file,
                        }
                        logging.debug(msg, msg_args)
                        self.update_section(var, enabled=False, file_path=file)

    def add_section(self, section, add_dict, file_path):
        # Create a new file if it does not exists
        if not os.path.isfile(file_path):
            with open(file_path, 'w+'):
                pass
        super(TripleOYumComposeRepoConfig, self).add_section(
            section, add_dict, file_path)

    def update_section(
            self, section, set_dict=None, enabled=None, file_path=None):
        update_dict = set_dict or {}
        if enabled is not None:
            update_dict['enabled'] = '1' if enabled else '0'
        if update_dict:
            super(TripleOYumComposeRepoConfig, self).update_section(
                section, update_dict, file_path=file_path)

    def update_all_sections(self, file_path, set_dict=None, enabled=None):
        update_dict = set_dict or {}
        if enabled is not None:
            update_dict['enabled'] = '1' if enabled else '0'
        if update_dict:
            super(TripleOYumComposeRepoConfig, self).update_all_sections(
                update_dict, file_path)
