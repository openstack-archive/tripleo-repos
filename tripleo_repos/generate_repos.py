#!/usr/bin/python
# Copyright 2020 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging
import os
import re
import requests
import subprocess

from cliff.command import Command

import tripleo_repos.constants as C
import tripleo_repos.templates as T
import tripleo_repos.exceptions as e


class GenerateRepos(Command):
    """Command to generate the repos"""

    log = logging.getLogger(__name__)

    def __init__(self, app, app_args, cmd_name=None):
        super(GenerateRepos, self).__init__(app, app_args, cmd_name)
        distro_info = self._get_distro()
        self.distro_id = distro_info[0]
        self.distro_major_version_id = distro_info[1]
        self.distro_name = distro_info[2]
        self.default_mirror = C.DEFAULT_MIRROR_MAP[self.distro_id]

    def take_action(self, parsed_args):
        self.log.debug('Running GenerateRepos command')
        if parsed_args.no_stream:
            parsed_args.stream = False
        parsed_args.old_mirror = self.default_mirror

        self._validate_args(parsed_args, self.distro_name)
        base_path = self._get_base_path(parsed_args)
        if parsed_args.distro in ['centos7']:
            self._install_priorities()
        self._remove_existing(parsed_args)
        self._install_repos(parsed_args, base_path)
        self._run_pkg_clean(parsed_args.distro)

    def get_parser(self, prog_name):
        parser = super(GenerateRepos, self).get_parser(prog_name)

        distro = "{}{}".format(self.distro_id, self.distro_major_version_id)

        # Calculating arguments default from constants
        distro_choices = ["".join(distro_pair)
                          for distro_pair in C.SUPPORTED_DISTROS]

        parser.add_argument('repos', metavar='REPO', nargs='+',
                            choices=['current', 'deps', 'current-tripleo',
                                     'current-tripleo-dev', 'ceph', 'opstools',
                                     'tripleo-ci-testing',
                                     'current-tripleo-rdo'],
                            help='A list of repos.  Available repos: '
                                 '%(choices)s.  The deps repo will always be '
                                 'included when using current or '
                                 'current-tripleo.  current-tripleo-dev '
                                 'downloads the current-tripleo, current, and '
                                 'deps repos, but sets the current repo to '
                                 'only be used for TripleO projects. '
                                 'It also modifies each repo\'s priority so '
                                 'packages are installed from the appropriate '
                                 'location.')
        parser.add_argument('-d', '--distro',
                            default=distro,
                            choices=distro_choices,
                            nargs='?',
                            help='Target distro with default detected at '
                            'runtime.'
                            )
        parser.add_argument('-b', '--branch',
                            default='master',
                            help='Target branch. Should be the lowercase '
                            'name of the OpenStack release. e.g. liberty')
        parser.add_argument('-o', '--output-path',
                            default=C.DEFAULT_OUTPUT_PATH,
                            help='Directory in which to save the selected '
                                 'repos.')
        parser.add_argument('--mirror',
                            default=self.default_mirror,
                            help='Server from which to install base OS '
                                 'packages. Default value is based on distro '
                                 'param.')
        parser.add_argument('--rdo-mirror',
                            default=C.DEFAULT_RDO_MIRROR,
                            help='Server from which to install RDO packages.')

        stream_group = parser.add_mutually_exclusive_group()
        stream_group.add_argument('--stream',
                                  action='store_true',
                                  default=True,
                                  help='Enable stream support for CentOS '
                                       'repos')
        stream_group.add_argument('--no-stream',
                                  action='store_true',
                                  default=False,
                                  help='Disable stream support for CentOS '
                                       'repos')

        return parser

    def _run_pkg_clean(self, distro):
        pkg_mgr = 'yum' if distro == 'centos7' else 'dnf'
        try:
            subprocess.check_call([pkg_mgr, 'clean', 'metadata'])
        except subprocess.CalledProcessError:
            self.log.error('Failed to clean yum metadata.')
            raise

    def _inject_mirrors(self, content, args):
        """Replace any references to the default mirrors in repo content

        In some cases we want to use mirrors whose repo files still point to
        the default servers.  If the user specified to use the mirror, we want
        to replace any such references with the mirror address.  This function
        handles that by using a regex to swap out the baseurl server.
        """

        content = re.sub('baseurl=%s' % C.DEFAULT_RDO_MIRROR,
                         'baseurl=%s' % args.rdo_mirror,
                         content)

        if args.old_mirror:
            content = re.sub('baseurl=%s' % args.old_mirror,
                             'baseurl=%s' % args.mirror,
                             content)

        return content

    def _get_repo(self, path, args):
        r = requests.get(path)
        if r.status_code == 200:
            return self._inject_mirrors(r.text, args)
        else:
            r.raise_for_status()

    def _write_repo(self, content, target, name=None):
        if not name:
            m = C.TITLE_RE.search(content)
            if not m:
                raise e.NoRepoTitle(
                    'Could not find repo title in: \n%s' % content)
            name = m.group(1)
            # centos-8 dlrn repos have changed. repos per component
            # are folded into a single repo.
            if 'component' in name:
                name = 'delorean'
        filename = name + '.repo'
        filename = os.path.join(target, filename)
        with open(filename, 'w') as f:
            f.write(content)
        self.log.info('Installed repo %s to %s' % (name, filename))

    def _change_priority(self, content, new_priority):
        new_content = C.PRIORITY_RE.sub('priority=%d' % new_priority, content)
        # This shouldn't happen, but let's be safe.
        if not C.PRIORITY_RE.search(new_content):
            new_content = []
            for line in content.split("\n"):
                new_content.append(line)
                if line.startswith('['):
                    new_content.append('priority=%d' % new_priority)
            new_content = "\n".join(new_content)
        return new_content

    def _create_ceph(self, args, release):
        """Generate a Ceph repo file for release"""
        centos_release = '7' if args.distro == 'centos7' else '8'
        return T.CEPH_REPO_TEMPLATE % {'centos_release': centos_release,
                                       'ceph_release': release,
                                       'mirror': args.mirror}

    def _add_includepkgs(self, content):
        new_content = []
        for line in content.split("\n"):
            new_content.append(line)
            if line.startswith('['):
                new_content.append(C.INCLUDE_PKGS)
        return "\n".join(new_content)

    # TODO: This need to be refactored
    def _install_repos(self, args, base_path):
        def install_deps(args, base_path):
            content = self._get_repo(base_path + 'delorean-deps.repo', args)
            self._write_repo(content, args.output_path)
        for repo in args.repos:
            if repo == 'current':
                content = self._get_repo(
                    base_path + 'current/delorean.repo', args)
                self._write_repo(content, args.output_path, name='delorean')
                install_deps(args, base_path)
            elif repo == 'deps':
                install_deps(args, base_path)
            elif repo == 'current-tripleo':
                content = self._get_repo(
                    base_path + 'current-tripleo/delorean.repo', args)
                self._write_repo(content, args.output_path)
                install_deps(args, base_path)
            elif repo == 'current-tripleo-dev':
                content = self._get_repo(
                    base_path + 'delorean-deps.repo', args)
                self._write_repo(content, args.output_path)
                content = self._get_repo(
                    base_path + 'current-tripleo/delorean.repo', args)
                content = C.TITLE_RE.sub('[\\1-current-tripleo]', content)
                content = C.NAME_RE.sub('name=\\1-current-tripleo', content)
                # We need to twiddle priorities since we're mixing multiple
                # repos that are generated with the same priority.
                content = self._change_priority(content, 20)
                self._write_repo(content, args.output_path,
                                 name='delorean-current-tripleo')
                content = self._get_repo(
                    base_path + 'current/delorean.repo', args)
                content = self._add_includepkgs(content)
                content = self._change_priority(content, 10)
                self._write_repo(content, args.output_path, name='delorean')
            elif repo == 'tripleo-ci-testing':
                content = self._get_repo(
                    base_path + 'tripleo-ci-testing/delorean.repo', args)
                self._write_repo(content, args.output_path)
                install_deps(args, base_path)
            elif repo == 'current-tripleo-rdo':
                content = self._get_repo(
                    base_path + 'current-tripleo-rdo/delorean.repo', args)
                self._write_repo(content, args.output_path)
                install_deps(args, base_path)
            elif repo == 'ceph':
                if args.branch in ['liberty', 'mitaka']:
                    content = self._create_ceph(args, 'hammer')
                elif args.branch in ['newton', 'ocata', 'pike']:
                    content = self._create_ceph(args, 'jewel')
                elif args.branch in ['queens', 'rocky']:
                    content = self._create_ceph(args, 'luminous')
                elif args.branch in ['stein', 'train', 'ussuri', 'victoria']:
                    content = self._create_ceph(args, 'nautilus')
                else:
                    content = self._create_ceph(args, 'pacific')
                self._write_repo(content, args.output_path)
            elif repo == 'opstools':
                content = T.OPSTOOLS_REPO_TEMPLATE % {'mirror': args.mirror}
                self._write_repo(content, args.output_path)
            else:
                raise e.InvalidArguments('Invalid repo "%s" specified' % repo)

        distro = args.distro
        # CentOS-8 AppStream is required for UBI-8
        if distro == 'ubi8':
            if not os.path.exists("/etc/distro.repos.d"):
                self.log.warning('For UBI it is recommended to create '
                                 '/etc/distro.repos.d and rerun!')
                dp_exists = False
            else:
                dp_exists = True
            if args.output_path == C.DEFAULT_OUTPUT_PATH and dp_exists:
                distro_path = "/etc/distro.repos.d"
            else:
                distro_path = args.output_path
            # TODO: Remove it once bugs are fixed
            # Add extra options to APPSTREAM_REPO_TEMPLATE because of
            # rhbz/1961558 and lpbz/1929634
            extra = ''
            if args.branch in ['train', 'ussuri', 'victoria']:
                extra = 'exclude=edk2-ovmf-20200602gitca407c7246bf-5*'
            content = T.APPSTREAM_REPO_TEMPLATE % {'mirror': args.mirror,
                                                   'extra': extra}
            self._write_repo(content, distro_path)
            content = T.BASE_REPO_TEMPLATE % {'mirror': args.mirror}
            self._write_repo(content, distro_path)
            distro = 'centos8'  # switch it to continue as centos8 distro

        # HA, Powertools are required for CentOS-8
        if distro == 'centos8':
            stream = '8'
            if args.stream and not args.no_stream:
                stream = stream + '-stream'
            content = T.HIGHAVAILABILITY_REPO_TEMPLATE % {
                'mirror': args.mirror, 'stream': stream}
            self._write_repo(content, args.output_path)
            content = T.POWERTOOLS_REPO_TEMPLATE % {'mirror': args.mirror,
                                                    'stream': stream}
            self._write_repo(content, args.output_path)

    def _install_priorities(self):
        try:
            subprocess.check_call(['yum', 'install', '-y',
                                   'yum-plugin-priorities'])
        except subprocess.CalledProcessError as e:
            self.log.error('Failed to install yum-plugin-priorities\n%s\n%s' %
                           (e.cmd, e.output))
            raise

    def _get_distro(self):
        """Get distro info from os-release

        returns: distro_id, distro_major_version_id, distro_name
        """

        output = subprocess.Popen(
            'source /etc/os-release && echo -e -n "$ID\n$VERSION_ID\n$NAME"',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=open(os.devnull, 'w'),
            executable='/bin/bash',
            universal_newlines=True).communicate()

        # distro_id and distro_version_id will always be at least an
        # empty string
        distro_id, distro_version_id, distro_name = output[0].split('\n')

        # if distro_version_id is empty string the major version will be empty
        # string too
        distro_major_version_id = distro_version_id.split('.')[0]

        # check if that is UBI subcase?
        if os.path.exists('/etc/yum.repos.d/ubi.repo'):
            distro_id = 'ubi'

        if (distro_id, distro_major_version_id) not in C.SUPPORTED_DISTROS:
            self.log.warning(
                "Unsupported platform '{}{}' detected by tripleo-repos,"
                " centos7 will be used unless you use CLI param to change it."
                "".format(distro_id, distro_major_version_id))
            distro_id = 'centos'
            distro_major_version_id = '7'

        if distro_id == 'ubi':
            self.log.warning(
                "Centos{} Base and AppStream will be installed for "
                "this UBI distro".format(distro_major_version_id))

        return distro_id, distro_major_version_id, distro_name

    def _remove_existing(self, args):
        """Remove any delorean* or opstools repos that already exist"""
        if args.distro == 'ubi8':
            regex = '^(BaseOS|AppStream|delorean|tripleo-centos-' \
                    '(opstools|ceph|highavailability|powertools)).*.repo'
        else:
            regex = '^(delorean|tripleo-centos-' \
                    '(opstools|ceph|highavailability|powertools)).*.repo'
        pattern = re.compile(regex)
        if os.path.exists("/etc/distro.repos.d"):
            paths = set(
                os.listdir(args.output_path) + os.listdir(
                    "/etc/distro.repos.d"))
        else:
            paths = os.listdir(args.output_path)
        for f in paths:
            if pattern.match(f):
                filename = os.path.join(args.output_path, f)
                if os.path.exists(filename):
                    os.remove(filename)
                    self.log.info('Removed old repo "%s"' % filename)
                filename = os.path.join("/etc/distro.repos.d", f)
                if os.path.exists(filename):
                    os.remove(filename)
                    self.log.info('Removed old repo "%s"' % filename)

    def _get_base_path(self, args):
        if args.distro == 'ubi8':
            # there are no base paths for UBI that work well
            distro = 'centos8'
        else:
            distro = args.distro

        # The mirror url with /$DISTRO$VERSION path for master branch is
        # deprecated.
        # The default for rdo mirrors is $DISTRO$VERSION-$BRANCH
        # it should work for every (distro, branch) pair that
        # makes sense
        # Any exception should be corrected at source, not here.
        distro_branch = '%s-%s' % (distro, args.branch)
        return '%s/%s/' % (args.rdo_mirror, distro_branch)

    # Validation functions

    def _validate_args(self, args, distro_name):
        self._validate_current_tripleo(args.repos)
        self._validate_distro_repos(args)
        self._validate_tripleo_ci_testing(args.repos)
        self._validate_distro_stream(args, distro_name)

    def _validate_distro_repos(self, args):
        """Validate requested repos are valid for the distro"""
        valid_repos = []
        if 'fedora' in args.distro:
            valid_repos = ['current', 'current-tripleo', 'ceph', 'deps',
                           'tripleo-ci-testing']
        elif args.distro in ['centos7', 'centos8', 'rhel8', 'ubi8']:
            valid_repos = ['ceph', 'current', 'current-tripleo',
                           'current-tripleo-dev', 'deps', 'tripleo-ci-testing',
                           'opstools', 'current-tripleo-rdo']
        invalid_repos = [x for x in args.repos if x not in valid_repos]
        if len(invalid_repos) > 0:
            raise e.InvalidArguments('{} repo(s) are not valid for {}. Valid '
                                     'repos are: {}'.format(invalid_repos,
                                                            args.distro,
                                                            valid_repos))
        return True

    def _validate_tripleo_ci_testing(self, repos):
        """Validate tripleo-ci-testing

        With tripleo-ci-testing for repo (currently only periodic container
        build) no other repos expected except optionally deps|ceph|opstools
        which is enabled regardless.
        """
        if 'tripleo-ci-testing' in repos and len(repos) > 1:
            if 'deps' in repos or 'ceph' in repos or 'opstools' in repos:
                return True
            else:
                raise e.InvalidArguments('Cannot use tripleo-ci-testing at the'
                                         ' same time as other repos, except '
                                         'deps|ceph|opstools.')
        return True

    def _validate_distro_stream(self, args, distro_name):
        """Validate stream related args vs host

        Fails if stream is to be used but the host isn't a stream OS or
        vice versa
        """
        is_stream = args.stream and not args.no_stream
        if is_stream and 'stream' not in distro_name.lower():
            raise e.InvalidArguments('--stream provided, but OS is not the '
                                     'Stream version. Please ensure the host '
                                     'is Stream.')
        elif not is_stream and 'stream' in distro_name.lower():
            raise e.InvalidArguments('--no-stream provided, but OS is the '
                                     'Stream version. Please ensure the host '
                                     'is not the Stream version.')
        return True

    def _validate_current_tripleo(self, repos):
        """Validate current usage

        current and current-tripleo cannot be specified with each other and
        current-tripleo-dev is a mix of current, current-tripleo and deps
        so they should not be specified on the command line with each other.
        """
        if 'current-tripleo' in repos and 'current' in repos:
            raise e.InvalidArguments(
                'Cannot use current and current-tripleo at the same time.')
        if 'current-tripleo-dev' not in repos:
            return True
        if 'current' in repos or 'current-tripleo' in repos or 'deps' in repos:
            raise e.InvalidArguments(
                'current-tripleo-dev should not be used with any other '
                'RDO Trunk repos.')
        return True
