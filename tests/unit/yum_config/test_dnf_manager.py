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
from unittest import mock

from . import test_main
import tripleo_repos.yum_config.dnf_manager as dnf_mgr


@ddt.ddt
class TestTripleODnfManager(test_main.TestTripleoYumConfigBase):
    """Tests for DnfModuleManager class and its methods."""

    def setUp(self):
        super(TestTripleODnfManager, self).setUp()
        self.dnf = dnf_mgr.DnfModuleManager()

    @ddt.data(
        {'module': 'fake', 'stream': None, 'profile': None},
        {'module': 'fake', 'stream': 'fake_stream', 'profile': None},
        {'module': 'fake', 'stream': None, 'profile': 'fake_prof'},
        {'module': 'fake', 'stream': 'fake_stream', 'profile': 'fake_prof'},
    )
    @ddt.unpack
    def test__get_module_spec(self, module, stream, profile):
        exp_str = module
        exp_str += ':' + stream if stream else ''
        exp_str += '/' + profile if profile else ''

        result = self.dnf._get_module_spec(module, stream=stream,
                                           profile=profile)

        self.assertEqual(exp_str, result)

    @ddt.data(Exception, RuntimeError)
    def test__do_transaction_failure(self, exc):
        mock_transaction = self.mock_object(
            self.dnf.base, 'do_transaction',
            mock.Mock(side_effect=exc))

        self.assertRaises(exc, self.dnf._do_transaction)

        mock_transaction.assert_called_once()

    @ddt.data('enable', 'disable', 'reset', 'install', 'remove')
    def test_module_operations(self, operation):
        fake_module = 'fake_module'
        fake_stream = 'fake_stream'
        fake_profile = 'fake_profile'
        mock_get_mod_spec = self.mock_object(self.dnf, '_get_module_spec')
        mock_op = self.mock_object(self.dnf.module_base, operation)
        mock_transaction = self.mock_object(self.dnf, '_do_transaction')

        dnf_method = getattr(self.dnf, operation + "_module")
        dnf_method(fake_module, stream=fake_stream, profile=fake_profile)

        mock_get_mod_spec.assert_called_once_with(
            fake_module, stream=fake_stream, profile=fake_profile)
        mock_op.assert_called_once()
        mock_transaction.assert_called_once()
