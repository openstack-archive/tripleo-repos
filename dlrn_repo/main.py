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
                'os-apply-config,os-cloud-config,os-collect-config,'
                'os-net-config,os-refresh-config,python-tripleoclient,'
                'tripleo-common,openstack -tripleo-heat-templates,'
                'openstack-tripleo-image-elements,openstack-tripleo,'
                'openstack-tripleo-puppet-elements,openstack-puppet-modules'
                )


class InvalidArguments(Exception):
    pass


class NoRepoTitle(Exception):
    pass


def _parse_args():
    parser = argparse.ArgumentParser(
        description='Download and instll dlrn repos. Note that these repos '
                    'require yum-plugin-priorities in order to function '
                    'correctly, so that will also be installed.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('repos', metavar='REPO', nargs='+',
                        help='A list of delorean repos. Available repos: '
                             'current, deps, current-tripleo. current-tripleo '
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
                        default='/etc/yum.repos.d',
                        help='Directory in which to save the selected dlrn '
                             'repos.')
    return parser.parse_args()


def _get_repo(path):
    r = requests.get(path)
    if r.status_code == 200:
        return r.text
    else:
        r.raise_for_status()


def _write_repo(content, target):
    m = TITLE_RE.match(content)
    if not m:
        raise NoRepoTitle('Could not find repo title in: \n%s' % content)
    filename = m.group(1) + '.repo'
    filename = os.path.join(target, filename)
    with open(filename, 'w') as f:
        f.write(content)
    print('Installed repo %s to %s' % (m.group(1), filename))


def _validate_args(args):
    if 'current-tripleo' in args.repos and len(args.repos) > 1:
        raise InvalidArguments('current-tripleo should not be used with any '
                               'other repos.')
    if args.branch != 'master' and 'current-tripleo' in args.repos:
        raise InvalidArguments('Cannot use current-tripleo on any branch '
                               'except master')
    if args.distro != 'centos7':
        raise InvalidArguments('centos7 is the only supported distro')


def _remove_existing(args):
    """Remove any delorean* repos that already exist"""
    for f in os.listdir(args.output_path):
        if f.startswith('delorean'):
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


def _change_priority(content, new_priority):
    new_content = PRIORITY_RE.sub('priority=%d' % new_priority, content)
    # This shouldn't happen, but let's be safe.
    if not PRIORITY_RE.search(new_content):
        new_content += '\npriority=%d' % new_priority
    return new_content


def _install_repos(args, base_path):
    for repo in args.repos:
        if repo == 'current':
            content = _get_repo(base_path + 'current/delorean.repo')
            if args.branch != 'master':
                content = TITLE_RE.sub('[delorean-%s]' % args.branch, content)
            _write_repo(content, args.output_path)
        elif repo == 'deps':
            content = _get_repo(base_path + 'delorean-deps.repo')
            _write_repo(content, args.output_path)
        elif repo == 'current-tripleo':
            content = _get_repo(base_path + 'delorean-deps.repo')
            # We need to twiddle priorities since we're mixing multiple repos
            # that are generated with the same priority.
            content = _change_priority(content, 30)
            _write_repo(content, args.output_path)
            content = _get_repo(base_path + 'current-tripleo/delorean.repo')
            content = TITLE_RE.sub('[delorean-current-tripleo]', content)
            content = _change_priority(content, 20)
            _write_repo(content, args.output_path)
            content = _get_repo(base_path + 'current/delorean.repo')
            content += '\n%s' % INCLUDE_PKGS
            content = _change_priority(content, 10)
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
