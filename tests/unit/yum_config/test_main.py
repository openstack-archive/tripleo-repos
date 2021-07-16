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

import ddt
import sys
import unittest
from unittest import mock

from . import fakes
from . import mock_modules  # noqa: F401
import tripleo_repos.yum_config.__main__ as main
import tripleo_repos.yum_config.yum_config as yum_cfg
import tripleo_repos.yum_config.dnf_manager as dnf_mgr


class TestTripleoYumConfigBase(unittest.TestCase):
    """Base test class for tripleo yum config module."""

    def mock_object(self, obj, attr, new_attr=None):
        if not new_attr:
            new_attr = mock.Mock()

        patcher = mock.patch.object(obj, attr, new_attr)
        patcher.start()
        # stop patcher at the end of the test
        self.addCleanup(patcher.stop)

        return new_attr


@ddt.ddt
class TestTripleoYumConfigMain(TestTripleoYumConfigBase):
    """Test class for main method operations."""

    def test_main_repo(self):
        sys.argv[1:] = ['repo', 'fake_repo', '--enable',
                        '--set-opts', 'key1=value1', 'key2=value2',
                        '--config-file-path', fakes.FAKE_FILE_PATH]
        yum_repo_obj = mock.Mock()
        mock_update_section = self.mock_object(yum_repo_obj, 'update_section')
        mock_yum_repo_obj = self.mock_object(
            yum_cfg, 'TripleOYumRepoConfig',
            mock.Mock(return_value=yum_repo_obj))

        main.main()
        expected_dict = {'key1': 'value1', 'key2': 'value2'}

        mock_yum_repo_obj.assert_called_once_with(
            file_path=fakes.FAKE_FILE_PATH, dir_path=None)
        mock_update_section.assert_called_once_with(
            'fake_repo', expected_dict, enable=True)

    @ddt.data('enable', 'disable', 'reset', 'install', 'remove')
    def test_main_module(self, operation):
        sys.argv[1:] = ['module', operation, 'fake_module', '--stream',
                        'fake_stream', '--profile', 'fake_profile']

        mock_dnf_mod = mock.Mock()
        mock_op = self.mock_object(mock_dnf_mod, operation + '_module')
        mock_dnf_mod_obj = self.mock_object(
            dnf_mgr, 'DnfModuleManager',
            mock.Mock(return_value=mock_dnf_mod))

        main.main()

        mock_dnf_mod_obj.assert_called_once()
        mock_op.assert_called_once_with(
            'fake_module', stream='fake_stream', profile='fake_profile')

    def test_main_global_conf(self):
        sys.argv[1:] = ['global', '--set-opts', 'key1=value1', 'key2=value2']
        yum_global_obj = mock.Mock()
        mock_update_section = self.mock_object(
            yum_global_obj, 'update_section')
        mock_yum_global_obj = self.mock_object(
            yum_cfg, 'TripleOYumGlobalConfig',
            mock.Mock(return_value=yum_global_obj))

        main.main()
        expected_dict = {'key1': 'value1', 'key2': 'value2'}

        mock_yum_global_obj.assert_called_once_with(file_path=None)
        mock_update_section.assert_called_once_with('main', expected_dict)

    def test_main_no_command(self):
        sys.argv[1:] = []
        with self.assertRaises(SystemExit) as command:
            main.main()

        self.assertEqual(2, command.exception.code)

    @ddt.data('repo')
    def test_main_repo_mod_without_name(self, command):
        sys.argv[1:] = [command, '--set-opts', 'key1=value1']

        with self.assertRaises(SystemExit) as command:
            main.main()

        self.assertEqual(2, command.exception.code)

    @ddt.data('key:value', 'value', 'key value')
    def test_main_invalid_options_format(self, option):
        sys.argv[1:] = ['global', '--set-opts', option]

        with self.assertRaises(SystemExit) as command:
            main.main()

        self.assertEqual(2, command.exception.code)
