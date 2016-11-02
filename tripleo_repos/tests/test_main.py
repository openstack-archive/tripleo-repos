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

import subprocess
import sys

import mock
import testtools

from tripleo_repos import main


class TestDlrnRepo(testtools.TestCase):
    @mock.patch('tripleo_repos.main._parse_args')
    @mock.patch('tripleo_repos.main._validate_args')
    @mock.patch('tripleo_repos.main._get_base_path')
    @mock.patch('tripleo_repos.main._install_priorities')
    @mock.patch('tripleo_repos.main._remove_existing')
    @mock.patch('tripleo_repos.main._install_repos')
    def test_main(self, mock_install, mock_remove, mock_ip, mock_gbp,
                  mock_validate, mock_parse):
        mock_args = mock.Mock()
        mock_parse.return_value = mock_args
        mock_path = mock.Mock()
        mock_gbp.return_value = mock_path
        main.main()
        mock_validate.assert_called_once_with(mock_args)
        mock_gbp.assert_called_once_with(mock_args)
        mock_ip.assert_called_once_with()
        mock_remove.assert_called_once_with(mock_args)
        mock_install.assert_called_once_with(mock_args, mock_path)

    @mock.patch('requests.get')
    def test_get_repo(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.text = '88MPH'
        mock_get.return_value = mock_response
        fake_addr = 'http://lone/pine/mall'
        content = main._get_repo(fake_addr)
        self.assertEqual('88MPH', content)
        mock_get.assert_called_once_with(fake_addr)

    @mock.patch('requests.get')
    def test_get_repo_404(self, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        fake_addr = 'http://twin/pines/mall'
        main._get_repo(fake_addr)
        mock_get.assert_called_once_with(fake_addr)
        mock_response.raise_for_status.assert_called_once_with()

    @mock.patch('os.listdir')
    @mock.patch('os.remove')
    def test_remove_existing(self, mock_remove, mock_listdir):
        fake_list = ['foo.repo', 'delorean.repo',
                     'delorean-current-tripleo.repo']
        mock_listdir.return_value = fake_list
        mock_args = mock.Mock()
        mock_args.output_path = '/etc/yum.repos.d'
        main._remove_existing(mock_args)
        self.assertIn(mock.call('/etc/yum.repos.d/delorean.repo'),
                      mock_remove.mock_calls)
        self.assertIn(mock.call('/etc/yum.repos.d/'
                                'delorean-current-tripleo.repo'),
                      mock_remove.mock_calls)
        self.assertNotIn(mock.call('/etc/yum.repos.d/foo.repo'),
                         mock_remove.mock_calls)

    def test_get_base_path(self):
        args = mock.Mock()
        args.branch = 'master'
        args.distro = 'centos7'
        path = main._get_base_path(args)
        self.assertEqual('http://trunk.rdoproject.org/centos7/', path)

    def test_get_base_path_branch(self):
        args = mock.Mock()
        args.branch = 'liberty'
        args.distro = 'centos7'
        path = main._get_base_path(args)
        self.assertEqual('http://trunk.rdoproject.org/centos7-liberty/', path)

    @mock.patch('subprocess.check_call')
    def test_install_priorities(self, mock_check_call):
        main._install_priorities()
        mock_check_call.assert_called_once_with(['yum', 'install', '-y',
                                                 'yum-plugin-priorities'])

    @mock.patch('subprocess.check_call')
    def test_install_priorities_fails(self, mock_check_call):
        mock_check_call.side_effect = subprocess.CalledProcessError(88, '88')
        self.assertRaises(subprocess.CalledProcessError,
                          main._install_priorities)

    @mock.patch('tripleo_repos.main._get_repo')
    @mock.patch('tripleo_repos.main._write_repo')
    def test_install_repos_current(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['current']
        args.branch = 'master'
        args.output_path = 'test'
        mock_get.return_value = '[delorean]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        mock_get.assert_called_once_with('roads/current/delorean.repo')
        mock_write.assert_called_once_with('[delorean]\nMr. Fusion', 'test')

    @mock.patch('tripleo_repos.main._get_repo')
    @mock.patch('tripleo_repos.main._write_repo')
    def test_install_repos_current_mitaka(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['current']
        args.branch = 'mitaka'
        args.output_path = 'test'
        mock_get.return_value = '[delorean]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        mock_get.assert_called_once_with('roads/current/delorean.repo')
        mock_write.assert_called_once_with('[delorean-mitaka]\nMr. Fusion',
                                           'test')

    @mock.patch('tripleo_repos.main._get_repo')
    @mock.patch('tripleo_repos.main._write_repo')
    def test_install_repos_deps(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['deps']
        args.branch = 'master'
        args.output_path = 'test'
        mock_get.return_value = '[delorean-deps]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        mock_get.assert_called_once_with('roads/delorean-deps.repo')
        mock_write.assert_called_once_with('[delorean-deps]\nMr. Fusion',
                                           'test')

    @mock.patch('tripleo_repos.main._get_repo')
    @mock.patch('tripleo_repos.main._write_repo')
    def test_install_repos_current_tripleo(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['current-tripleo']
        args.branch = 'master'
        args.output_path = 'test'
        mock_get.return_value = '[delorean]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        mock_get.assert_called_once_with('http://buildlogs.centos.org/centos/'
                                         '7/cloud/x86_64/rdo-trunk-master-'
                                         'tripleo/delorean.repo')
        mock_write.assert_called_once_with('[delorean]\nMr. Fusion', 'test')

    @mock.patch('tripleo_repos.main._get_repo')
    @mock.patch('tripleo_repos.main._write_repo')
    def test_install_repos_current_tripleo_dev(self, mock_write, mock_get):
        args = mock.Mock()
        args.repos = ['current-tripleo-dev']
        args.branch = 'master'
        args.output_path = 'test'
        mock_get.return_value = '[delorean]\nMr. Fusion'
        main._install_repos(args, 'roads/')
        mock_get.assert_any_call('roads/delorean-deps.repo')
        # This is the wrong name for the deps repo, but I'm not bothered
        # enough by that to mess with mocking multiple different calls.
        mock_write.assert_any_call('[delorean]\n'
                                   'Mr. Fusion\npriority=30', 'test')
        mock_get.assert_any_call('http://buildlogs.centos.org/centos/'
                                 '7/cloud/x86_64/rdo-trunk-master-'
                                 'tripleo/delorean.repo')
        mock_write.assert_any_call('[delorean-current-tripleo]\n'
                                   'Mr. Fusion\npriority=20', 'test')
        mock_get.assert_called_with('roads/current/delorean.repo')
        mock_write.assert_called_with('[delorean]\nMr. Fusion\n%s\n'
                                      'priority=10' %
                                      main.INCLUDE_PKGS, 'test')

    def test_install_repos_invalid(self):
        args = mock.Mock()
        args.repos = ['roads?']
        self.assertRaises(main.InvalidArguments, main._install_repos, args,
                          'roads/')

    def test_write_repo(self):
        m = mock.mock_open()
        with mock.patch('tripleo_repos.main.open', m, create=True):
            main._write_repo('[delorean]\nThis=Heavy', 'test')
        m.assert_called_once_with('test/delorean.repo', 'w')
        m().write.assert_called_once_with('[delorean]\nThis=Heavy')

    def test_write_repo_invalid(self):
        self.assertRaises(main.NoRepoTitle, main._write_repo, 'Great Scot!',
                          'test')

    def test_parse_args(self):
        with mock.patch.object(sys, 'argv', ['', 'current', 'deps', '-d',
                                             'centos7', '-b', 'liberty',
                                             '-o', 'test']):
            args = main._parse_args()
        self.assertEqual(['current', 'deps'], args.repos)
        self.assertEqual('centos7', args.distro)
        self.assertEqual('liberty', args.branch)
        self.assertEqual('test', args.output_path)

    def test_parse_args_long(self):
        with mock.patch.object(sys, 'argv', ['', 'current', '--distro',
                                             'centos7', '--branch',
                                             'mitaka', '--output-path',
                                             'test']):
            args = main._parse_args()
        self.assertEqual(['current'], args.repos)
        self.assertEqual('centos7', args.distro)
        self.assertEqual('mitaka', args.branch)
        self.assertEqual('test', args.output_path)

    def test_change_priority(self):
        result = main._change_priority('[delorean]\npriority=1', 10)
        self.assertEqual('[delorean]\npriority=10', result)

    def test_change_priority_none(self):
        result = main._change_priority('[delorean]', 10)
        self.assertEqual('[delorean]\npriority=10', result)


class TestValidate(testtools.TestCase):
    def setUp(self):
        super(TestValidate, self).setUp()
        self.args = mock.Mock()
        self.args.repos = ['current']
        self.args.branch = 'master'
        self.args.distro = 'centos7'

    def test_good(self):
        main._validate_args(self.args)

    def test_current_and_tripleo_dev(self):
        self.args.repos = ['current', 'current-tripleo-dev']
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args)

    def test_deps_and_tripleo_dev(self):
        self.args.repos = ['deps', 'current-tripleo-dev']
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args)

    def test_branch_and_tripleo_dev(self):
        self.args.repos = ['current-tripleo-dev']
        self.args.branch = 'liberty'
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args)

    def test_current_and_tripleo(self):
        self.args.repos = ['current', 'current-tripleo']
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args)

    def test_deps_and_tripleo_allowed(self):
        self.args.repos = ['deps', 'current-tripleo']
        main._validate_args(self.args)

    def test_branch_and_tripleo(self):
        self.args.repos = ['current-tripleo']
        self.args.branch = 'liberty'
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args)

    def test_invalid_distro(self):
        self.args.distro = 'Jigawatts 1.21'
        self.assertRaises(main.InvalidArguments, main._validate_args,
                          self.args)
