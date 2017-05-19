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

import argparse
import os
import re
import subprocess

import requests


TITLE_RE = re.compile('\[(.*)\]')
PRIORITY_RE = re.compile('priority=\d+')
# Packages to be included from delorean-current when using current-tripleo
INCLUDE_PKGS = ('includepkgs=diskimage-builder,instack,instack-undercloud,'
                'os-apply-config,os-collect-config,os-net-config,'
                'os-refresh-config,python-tripleoclient,'
                'openstack-tripleo-common*,openstack-tripleo-heat-templates,'
                'openstack-tripleo-image-elements,openstack-tripleo,'
                'openstack-tripleo-puppet-elements,openstack-puppet-modules,'
                'openstack-tripleo-ui,puppet-*')
OPSTOOLS_REPO_URL = ('https://raw.githubusercontent.com/centos-opstools/'
                     'opstools-repo/master/opstools.repo')
DEFAULT_OUTPUT_PATH = '/etc/yum.repos.d'


class InvalidArguments(Exception):
    pass


class NoRepoTitle(Exception):
    pass


def _parse_args():
    parser = argparse.ArgumentParser(
        description='Download and install repos necessary for TripleO. Note '
                    'that some of these repos require yum-plugin-priorities, '
                    'so that will also be installed.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('repos', metavar='REPO', nargs='+',
                        choices=['current', 'deps', 'current-tripleo',
                                 'current-tripleo-dev', 'ceph', 'opstools'],
                        help='A list of repos.  Available repos: '
                             '%(choices)s.  The deps repo will always be '
                             'included when using current or '
                             'current-tripleo.  current-tripleo-dev '
                             'downloads the current-tripleo, current, and '
                             'deps repos, but sets the current repo to only '
                             'be used for TripleO projects. It also modifies '
                             'each repo\'s priority so packages are installed '
                             'from the appropriate location.')
    parser.add_argument('-d', '--distro',
                        default='centos7',
                        help='Target distro. Currently only centos7 is '
                             'supported')
    parser.add_argument('-b', '--branch',
                        default='master',
                        help='Target branch. Should be the lowercase name of '
                             'the OpenStack release. e.g. liberty')
    parser.add_argument('-o', '--output-path',
                        default=DEFAULT_OUTPUT_PATH,
                        help='Directory in which to save the selected repos.')
    return parser.parse_args()


def _get_repo(path):
    r = requests.get(path)
    if r.status_code == 200:
        return r.text
    else:
        r.raise_for_status()


def _write_repo(content, target):
    m = TITLE_RE.search(content)
    if not m:
        raise NoRepoTitle('Could not find repo title in: \n%s' % content)
    filename = m.group(1) + '.repo'
    filename = os.path.join(target, filename)
    with open(filename, 'w') as f:
        f.write(content)
    print('Installed repo %s to %s' % (m.group(1), filename))


def _validate_args(args):
    if ('current-tripleo-dev' in args.repos and
            ('current' in args.repos or 'current-tripleo' in args.repos or
             'deps' in args.repos)):
        raise InvalidArguments('current-tripleo-dev should not be used with '
                               'any other dlrn repos.')
    if args.branch != 'master' and ('current-tripleo-dev' in args.repos or
                                    'current-tripleo' in args.repos):
        raise InvalidArguments('Cannot use current-tripleo on any branch '
                               'except master')
    if 'current-tripleo' in args.repos and 'current' in args.repos:
        raise InvalidArguments('Cannot use current and current-tripleo at the '
                               'same time.')
    if args.distro != 'centos7':
        raise InvalidArguments('centos7 is the only supported distro')
    if 'ceph' in args.repos and args.output_path != DEFAULT_OUTPUT_PATH:
        raise InvalidArguments('The Ceph repo is installed from a package and '
                               'cannot be installed to a custom location.')


def _remove_existing(args):
    """Remove any delorean* or opstools repos that already exist"""
    for f in os.listdir(args.output_path):
        if f.startswith('delorean') or f == 'centos-opstools.repo':
            filename = os.path.join(args.output_path, f)
            os.remove(filename)
            print('Removed old repo "%s"' % filename)


def _get_base_path(args):
    if args.branch != 'master':
        distro_branch = '%s-%s' % (args.distro, args.branch)
    else:
        distro_branch = args.distro
    return 'http://trunk.rdoproject.org/%s/' % distro_branch


def _install_priorities():
    try:
        subprocess.check_call(['yum', 'install', '-y',
                               'yum-plugin-priorities'])
    except subprocess.CalledProcessError:
        print('ERROR: Failed to install yum-plugin-priorities.')
        raise


def _install_ceph(release):
    """Install the Ceph repo specified by release"""
    # Make sure we're starting with a clean slate
    try:
        print('Cleaning up existing ceph repos')
        subprocess.check_call(['yum', 'remove', '-y', 'centos-release-ceph-*'])
    except subprocess.CalledProcessError:
        print('ERROR: Failed to clean up ceph release package')
        raise

    pkg_name = 'centos-release-ceph-%s' % release
    try:
        subprocess.check_call(['yum', 'install', '-y', '--enablerepo=extras',
                               pkg_name])
    except subprocess.CalledProcessError:
        print('ERROR: Failed to install %s.' % pkg_name)
        raise
    subprocess.check_call(['sed', '-i', '-e',
                           's/gpgcheck=.*/gpgcheck=0/',
                           '/etc/yum.repos.d/CentOS-Ceph-%s.repo' %
                           release.title()])
    print('Installed repo for Ceph release %s' % release)


def _change_priority(content, new_priority):
    new_content = PRIORITY_RE.sub('priority=%d' % new_priority, content)
    # This shouldn't happen, but let's be safe.
    if not PRIORITY_RE.search(new_content):
        new_content += '\npriority=%d' % new_priority
    return new_content


def _install_repos(args, base_path):
    # NOTE(bnemec): If/when we support a distro other than centos7 we'll need
    # a way to handle setting this appropriately.
    current_tripleo_repo = ('http://buildlogs.centos.org/centos/7/cloud/x86_64'
                            '/rdo-trunk-master-tripleo/delorean.repo')

    def install_deps(args, base_path):
        content = _get_repo(base_path + 'delorean-deps.repo')
        _write_repo(content, args.output_path)

    for repo in args.repos:
        if repo == 'current':
            content = _get_repo(base_path + 'current/delorean.repo')
            if args.branch != 'master':
                content = TITLE_RE.sub('[delorean-%s]' % args.branch, content)
            _write_repo(content, args.output_path)
            install_deps(args, base_path)
        elif repo == 'deps':
            install_deps(args, base_path)
        elif repo == 'current-tripleo':
            content = _get_repo(current_tripleo_repo)
            _write_repo(content, args.output_path)
            install_deps(args, base_path)
        elif repo == 'current-tripleo-dev':
            content = _get_repo(base_path + 'delorean-deps.repo')
            _write_repo(content, args.output_path)
            content = _get_repo(current_tripleo_repo)
            content = TITLE_RE.sub('[delorean-current-tripleo]', content)
            # We need to twiddle priorities since we're mixing multiple repos
            # that are generated with the same priority.
            content = _change_priority(content, 20)
            _write_repo(content, args.output_path)
            content = _get_repo(base_path + 'current/delorean.repo')
            content += '\n%s' % INCLUDE_PKGS
            content = _change_priority(content, 10)
            _write_repo(content, args.output_path)
        elif repo == 'ceph':
            if args.branch in ['liberty', 'mitaka']:
                _install_ceph('hammer')
            else:
                _install_ceph('jewel')
        elif repo == 'opstools':
            content = _get_repo(OPSTOOLS_REPO_URL)
            _write_repo(content, args.output_path)
        else:
            raise InvalidArguments('Invalid repo "%s" specified' % repo)


def main():
    args = _parse_args()
    _validate_args(args)
    base_path = _get_base_path(args)
    _install_priorities()
    _remove_existing(args)
    _install_repos(args, base_path)


if __name__ == '__main__':
    main()
