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

from __future__ import print_function
import argparse
import os
import re
import subprocess
import sys

import requests


TITLE_RE = re.compile('\\[(.*)\\]')
PRIORITY_RE = re.compile('priority=\\d+')
# Packages to be included from delorean-current when using current-tripleo
INCLUDE_PKGS = ('includepkgs=instack,instack-undercloud,'
                'os-apply-config,os-collect-config,os-net-config,'
                'os-refresh-config,python*-tripleoclient,'
                'openstack-tripleo-*,openstack-puppet-modules,'
                'puppet-*,python*-tripleo-common,python*-paunch*')
DEFAULT_OUTPUT_PATH = '/etc/yum.repos.d'
DEFAULT_RDO_MIRROR = 'https://trunk.rdoproject.org'
RDO_RE = re.compile('baseurl=%s' % DEFAULT_RDO_MIRROR)

DEFAULT_MIRROR_MAP = {
    'fedora': 'https://mirrors.fedoraproject.org',
    'centos': 'http://mirror.centos.org'
}
CEPH_REPO_TEMPLATE = '''
[tripleo-centos-ceph-%(ceph_release)s]
name=tripleo-centos-ceph-%(ceph_release)s
baseurl=%(centos_mirror)s/centos/7/storage/x86_64/ceph-%(ceph_release)s/
gpgcheck=0
enabled=1
'''
OPSTOOLS_REPO_TEMPLATE = '''
[tripleo-centos-opstools]
name=tripleo-centos-opstools
baseurl=%s/centos/7/opstools/x86_64/
gpgcheck=0
enabled=1
'''
# unversioned fedora added for backwards compatibility
SUPPORTED_DISTROS = ['centos7', 'fedora28', 'fedora']


class InvalidArguments(Exception):
    pass


class NoRepoTitle(Exception):
    pass


def _parse_args():

    distro = subprocess.Popen(
        'source /etc/os-release && echo "$ID$VERSION_ID"',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=open(os.devnull, 'w'),
        universal_newlines=True).communicate()[0].rstrip()

    if distro not in SUPPORTED_DISTROS:
        print(
            "WARNING: Unsupported platform '%s' detected by tripleo-repos, "
            "centos7 will be used unless you use CLI param to change it." %
            distro, file=sys.stderr)
        distro = 'centos7'
    distro_key = re.sub(r'[0-9]+', '', distro)

    parser = argparse.ArgumentParser(
        description='Download and install repos necessary for TripleO. Note '
                    'that some of these repos require yum-plugin-priorities, '
                    'so that will also be installed.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('repos', metavar='REPO', nargs='+',
                        choices=['current', 'deps', 'current-tripleo',
                                 'current-tripleo-dev', 'ceph', 'opstools',
                                 'tripleo-ci-testing'],
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
                        default=distro,
                        choices=SUPPORTED_DISTROS,
                        nargs='?',
                        help='Target distro with default detected at runtime. '
                        )
    parser.add_argument('-b', '--branch',
                        default='master',
                        help='Target branch. Should be the lowercase name of '
                             'the OpenStack release. e.g. liberty')
    parser.add_argument('-o', '--output-path',
                        default=DEFAULT_OUTPUT_PATH,
                        help='Directory in which to save the selected repos.')
    parser.add_argument('--mirror',
                        default=DEFAULT_MIRROR_MAP[distro_key],
                        help='Server from which to install base OS packages. '
                             'Default value is based on distro param.')
    parser.add_argument('--centos-mirror',
                        default=DEFAULT_MIRROR_MAP[distro_key],
                        help='[deprecated] Server from which to install base '
                             'CentOS packages. If mentioned it will be used '
                             'as --mirror for backwards compatibility.')
    parser.add_argument('--rdo-mirror',
                        default=DEFAULT_RDO_MIRROR,
                        help='Server from which to install RDO packages.')

    args = parser.parse_args()
    if args.centos_mirror:
        print("WARNING: --centos-mirror was deprecated in favour of --mirror",
              file=sys.stderr)
        args.mirror = args.centos_mirror

    distro_key = re.sub(r'[0-9]+', '', args.distro)
    args.old_mirror = DEFAULT_MIRROR_MAP[distro_key]

    return args


def _get_repo(path, args):
    r = requests.get(path)
    if r.status_code == 200:
        return _inject_mirrors(r.text, args)
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


def _validate_distro_repos(args):
    """Validate requested repos are valid for the distro"""
    valid_repos = []
    if 'fedora' in args.distro:
        valid_repos = ['current', 'current-tripleo', 'ceph', 'deps',
                       'tripleo-ci-testing']
    elif args.distro in ['centos7']:
        valid_repos = ['ceph', 'current', 'current-tripleo',
                       'current-tripleo-dev', 'deps', 'tripleo-ci-testing']
    invalid_repos = [x for x in args.repos if x not in valid_repos]
    if len(invalid_repos) > 0:
        raise InvalidArguments('{} repo(s) are not valid for {}. Valid repos '
                               'are: {}'.format(invalid_repos, args.distro,
                                                valid_repos))
    return True


def _validate_current_tripleo(repos):
    """Validate current usage

    current and current-tripleo cannot be specified with each other and
    current-tripleo-dev is a mix of current, current-tripleo and deps
    so they should not be specified on the command line with each other.
    """
    if 'current-tripleo' in repos and 'current' in repos:
        raise InvalidArguments('Cannot use current and current-tripleo at the '
                               'same time.')
    if 'current-tripleo-dev' not in repos:
        return True
    if 'current' in repos or 'current-tripleo' in repos or 'deps' in repos:
        raise InvalidArguments('current-tripleo-dev should not be used with '
                               'any other RDO Trunk repos.')
    return True


def _validate_tripleo_ci_testing(repos):
    """Validate tripleo-ci-testing

    With tripleo-ci-testing for repo (currently only periodic container build)
    no other repos expected except optionally deps which is enabled regardless.
    """
    if 'tripleo-ci-testing' in repos and len(repos) > 1:
        if 'deps' in repos and len(repos) == 2:
            return True
        else:
            raise InvalidArguments('Cannot use tripleo-ci-testing at the '
                                   'same time as other repos, except deps.')
    return True


def _validate_args(args):
    _validate_current_tripleo(args.repos)
    _validate_distro_repos(args)
    _validate_tripleo_ci_testing(args.repos)


def _remove_existing(args):
    """Remove any delorean* or opstools repos that already exist"""
    pattern = re.compile('^(delorean|tripleo-centos-(opstools|ceph)).*.repo')
    for f in os.listdir(args.output_path):
        if pattern.match(f):
            filename = os.path.join(args.output_path, f)
            os.remove(filename)
            print('Removed old repo "%s"' % filename)


def _get_base_path(args):
    if args.branch != 'master':
        if args.distro not in ['centos7']:
            raise InvalidArguments('Branches only suppported with centos7')
        distro_branch = '%s-%s' % (args.distro, args.branch)
    else:
        distro_branch = args.distro
    return '%s/%s/' % (args.rdo_mirror, distro_branch)


def _install_priorities():
    try:
        subprocess.check_call(['yum', 'install', '-y',
                               'yum-plugin-priorities'])
    except subprocess.CalledProcessError as e:
        print('ERROR: Failed to install yum-plugin-priorities\n%s\n%s' %
              (e.cmd, e.output))
        raise


def _create_ceph(args, release):
    """Generate a Ceph repo file for release"""
    return CEPH_REPO_TEMPLATE % {'ceph_release': release,
                                 'centos_mirror': args.centos_mirror}


def _change_priority(content, new_priority):
    new_content = PRIORITY_RE.sub('priority=%d' % new_priority, content)
    # This shouldn't happen, but let's be safe.
    if not PRIORITY_RE.search(new_content):
        new_content += '\npriority=%d' % new_priority
    return new_content


def _inject_mirrors(content, args):
    """Replace any references to the default mirrors in repo content

    In some cases we want to use mirrors whose repo files still point to the
    default servers.  If the user specified to use the mirror, we want to
    replace any such references with the mirror address.  This function
    handles that by using a regex to swap out the baseurl server.
    """
    new_content = RDO_RE.sub('baseurl=%s' % args.rdo_mirror, content)

    r = re.compile('baseurl=%s' % args.old_mirror)
    new_content = r.sub('baseurl=%s' % args.mirror, new_content)

    return new_content


def _install_repos(args, base_path):
    def install_deps(args, base_path):
        content = _get_repo(base_path + 'delorean-deps.repo', args)
        _write_repo(content, args.output_path)

    for repo in args.repos:
        if repo == 'current':
            content = _get_repo(base_path + 'current/delorean.repo', args)
            if args.branch != 'master':
                content = TITLE_RE.sub('[delorean-%s]' % args.branch, content)
            _write_repo(content, args.output_path)
            install_deps(args, base_path)
        elif repo == 'deps':
            install_deps(args, base_path)
        elif repo == 'current-tripleo':
            content = _get_repo(base_path + 'current-tripleo/delorean.repo',
                                args)
            _write_repo(content, args.output_path)
            install_deps(args, base_path)
        elif repo == 'current-tripleo-dev':
            content = _get_repo(base_path + 'delorean-deps.repo', args)
            _write_repo(content, args.output_path)
            content = _get_repo(base_path + 'current-tripleo/delorean.repo',
                                args)
            content = TITLE_RE.sub('[delorean-current-tripleo]', content)
            # We need to twiddle priorities since we're mixing multiple repos
            # that are generated with the same priority.
            content = _change_priority(content, 20)
            _write_repo(content, args.output_path)
            content = _get_repo(base_path + 'current/delorean.repo', args)
            content += '\n%s' % INCLUDE_PKGS
            content = _change_priority(content, 10)
            _write_repo(content, args.output_path)
        elif repo == 'tripleo-ci-testing':
            content = _get_repo(base_path + 'tripleo-ci-testing/delorean.repo',
                                args)
            _write_repo(content, args.output_path)
            install_deps(args, base_path)
        elif repo == 'ceph':
            if args.branch in ['liberty', 'mitaka']:
                content = _create_ceph(args, 'hammer')
            elif args.branch in ['newton', 'ocata', 'pike']:
                content = _create_ceph(args, 'jewel')
            else:
                content = _create_ceph(args, 'luminous')
            _write_repo(content, args.output_path)
        elif repo == 'opstools':
            content = OPSTOOLS_REPO_TEMPLATE % args.centos_mirror
            _write_repo(content, args.output_path)
        else:
            raise InvalidArguments('Invalid repo "%s" specified' % repo)


def _run_pkg_clean(distro):
    pkg_mgr = 'yum' if distro == 'centos7' else 'dnf'
    try:
        subprocess.check_call([pkg_mgr, 'clean', 'metadata'])
    except subprocess.CalledProcessError:
        print('ERROR: Failed to clean yum metadata.')
        raise


def main():
    args = _parse_args()
    _validate_args(args)
    base_path = _get_base_path(args)
    if args.distro in ['centos7']:
        _install_priorities()
    _remove_existing(args)
    _install_repos(args, base_path)
    _run_pkg_clean(args.distro)


if __name__ == '__main__':
    main()
