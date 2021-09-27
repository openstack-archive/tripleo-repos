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

import copy
import json
import os
from unittest import mock
import urllib.request

from . import fakes
from . import test_main
import tripleo_repos.yum_config.constants as const
import tripleo_repos.yum_config.exceptions as exc
import tripleo_repos.yum_config.compose_repos as repos
import tripleo_repos.yum_config.yum_config as yum_config


class TestTripleOComposeRepos(test_main.TestTripleoYumConfigBase):
    """Tests for TripleComposeRepos class and its methods."""
    def setUp(self):
        super(TestTripleOComposeRepos, self).setUp()
        self.repos = self._create_compose_repos_obj(
            dir_path='/tmp'
        )

    def _create_compose_repos_obj(
            self,
            compose_url=fakes.FAKE_COMPOSE_URL,
            release=const.COMPOSE_REPOS_RELEASES[0],
            dir_path=None,
            arch=const.COMPOSE_REPOS_SUPPORTED_ARCHS[0]):

        url_res = mock.Mock()
        json_data = json.dumps(fakes.FAKE_COMPOSE_INFO)
        self.mock_object(urllib.request, "urlopen",
                         mock.Mock(return_value=url_res))
        self.mock_object(url_res, 'read',
                         mock.Mock(return_value=json_data))

        return repos.TripleOYumComposeRepoConfig(
            compose_url, release, dir_path=dir_path, arch=arch)

    def test_tripleo_compose_repos_invalid_release(self):
        self.assertRaises(exc.TripleOYumConfigComposeError,
                          repos.TripleOYumComposeRepoConfig,
                          fakes.FAKE_COMPOSE_URL,
                          'invalid_release')

    def test_tripleo_compose_repos_invalid_url(self):
        self.assertRaises(exc.TripleOYumConfigComposeError,
                          repos.TripleOYumComposeRepoConfig,
                          "http://invalid_url.org",
                          const.COMPOSE_REPOS_RELEASES[0])

    def test__get_compose_info_exc(self):
        self.mock_object(urllib.request, "urlopen",
                         mock.Mock(side_effect=Exception))

        self.assertRaises(exc.TripleOYumConfigComposeError,
                          self.repos._get_compose_info)

    def test_enable_compose_repos(self):
        self.mock_object(self.repos, 'add_section')
        self.repos.enable_compose_repos(
            variants=fakes.FAKE_COMPOSE_INFO['payload']['variants'].keys(),
            override_repos=False
        )

    @mock.patch('builtins.open')
    def test_add_section(self, open):
        self.mock_object(os.path, 'isfile', mock.Mock(return_value=False))
        mock_add_section = self.mock_object(yum_config.TripleOYumConfig,
                                            "add_section")

        self.repos.add_section(fakes.FAKE_SECTION1, fakes.FAKE_SET_DICT,
                               fakes.FAKE_FILE_PATH)

        mock_add_section.assert_called_once_with(
            fakes.FAKE_SECTION1, fakes.FAKE_SET_DICT, fakes.FAKE_FILE_PATH
        )

    def test_update_section(self):
        mock_update = self.mock_object(yum_config.TripleOYumConfig,
                                       "update_section")
        expected_set_dict = copy.deepcopy(fakes.FAKE_SET_DICT)
        expected_set_dict['enabled'] = '1'

        self.repos.update_section(fakes.FAKE_SECTION1,
                                  set_dict=fakes.FAKE_SET_DICT,
                                  enabled=True,
                                  file_path=fakes.FAKE_FILE_PATH)

        mock_update.assert_called_once_with(fakes.FAKE_SECTION1,
                                            expected_set_dict,
                                            file_path=fakes.FAKE_FILE_PATH)

    def test_update_all_sections(self):
        mock_update = self.mock_object(yum_config.TripleOYumConfig,
                                       "update_all_sections")
        expected_set_dict = copy.deepcopy(fakes.FAKE_SET_DICT)
        expected_set_dict['enabled'] = '0'

        self.repos.update_all_sections(fakes.FAKE_FILE_PATH,
                                       set_dict=fakes.FAKE_SET_DICT,
                                       enabled=False)

        mock_update.assert_called_once_with(expected_set_dict,
                                            fakes.FAKE_FILE_PATH)
