#!/usr/bin/python
# Copyright 2021 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)


__metaclass__ = type
DOCUMENTATION = r'''
---
module: yum_config

short_description: Update yum configuration files for TripleO deployments.

version_added: "1.0.0"

description:
    - Update specific options for different yum configuration files like
      yum repos, yum modules and yum global configuration.

options:
    type:
        description:
          - The type of yum configuration to be changed.
        required: true
        type: str
        choices: [repo, module, global, 'enable-compose-repos']
    name:
        description:
          - Name of the repo or module to be changed. This options is
            mandatory only for repo and module types.
        type: str
    enabled:
        description:
          - Change the yum repo or module to enabled or disabled.
          - This options is ignored for yum global configuration.
        type: bool
        default: true
    operation:
        description:
          - Operation to be execute within a dnf module.
        type: str
        choices: [install, remove, reset]
    stream:
        description:
          - Sets a module stream. This options is recommended when enabling a
            module that doesn't have a default stream.
        type: str
    profile:
        description:
          - Sets a module profile. This options is recommended when installing
            a module that doesn't have a default profile.
        type: str
    set_options:
        description:
          - Dictionary with options to be updated. All dictionary values must
            be string or list of strings.
        type: dict
    file_path:
        description:
          - Absolute path of the configuration file to be changed.
        type: path
    dir_path:
        description:
          - Absolute path of the directory that contains the configuration
            file to be changed.
        type: path
        default: /etc/yum.repos.d
    environment_file:
        description:
          - Absolute path to an environment file to be read before updating or
            creating yum config and repo files.
        type: path
    compose_url:
        description:
          - URL that contains CentOS compose repositories.
        type: str
    centos_release:
        description:
          - Target CentOS release.
        type: str
        choices: [centos-stream-8, centos-stream-9]
    arch:
        description:
          - System architecture which the repos will be configure.
        type: str
        choices: [aarch64, ppc64le, x86_64]
        default: x86_64
    variants:
        description:
          - Repository variants that should be configured. If not provided,
            all available variants will be configured.
        type: list
        elements: str
    disable_conflicting_variants:
        description:
          - Disable all repos from the same directory that match variants'
            name.
        type: bool
        default: false
    disable_repos:
        description:
          - List with file path of repos that should be disabled after
            successfully enabling all compose repos.
        type: list
        elements: str

author:
    - Douglas Viroel (@viroel)
'''

EXAMPLES = r'''
# Set yum 'appstream' repo to enabled and exclude a list of packages
- name: Enable appstream repo and exclude nodejs and mariadb packages
  become: true
  become_user: root
  tripleo_yum_config:
    type: repo
    name: appstream
    enabled: true
    set_options:
      exclude:
        - nodejs*
        - mariadb*

# Enable and install a yum/dnf module
- name: Enable nginx module
  become: true
  become_user: root
  tripleo_yum_config:
    type: module
    name: tomcat
    enabled: false
    stream: "1.18"

- name: Enable nginx module
  become: true
  become_user: root
  tripleo_yum_config:
    type: module
    name: nginx
    operation: install
    profile: common

# Set yum global configuration options
- name: Set yum global options
  become: true
  become_user: root
  tripleo_yum_config:
    type: global
    file_path: /etc/dnf/dnf.conf
    set_options:
      skip_if_unavailable: "False"
      keepcache: "0"

- name: Configure a set of repos based on latest CentOS Stream 8 compose
  become: true
  become_user: root
  tripleo_yum_config:
    compose_url: https://composes.centos.org/latest-CentOS-Stream-8/compose/
    centos_release: centos-stream-8
    variants:
      - AppStream
      - BaseOS
    disable_conflicting_variants: true
    disable_repos:
      - /etc/yum.repos.d/CentOS-Linux-AppStream.repo
      - /etc/yum.repos.d/CentOS-Linux-BaseOS.repo
'''

RETURN = r''' # '''

from ansible.module_utils import six  # noqa: E402
from ansible.module_utils.basic import AnsibleModule  # noqa: E402


def run_module():
    try:
        import ansible_collections.tripleo.repos.plugins.module_utils. \
            tripleo_repos.yum_config.constants as const
        import ansible_collections.tripleo.repos.plugins.module_utils. \
            tripleo_repos.yum_config.utils as utils
    except ImportError:
        import tripleo_repos.yum_config.constants as const
        import tripleo_repos.yum_config.utils as utils

    supported_config_types = ['repo', 'global', 'module',
                              'enable-compose-repos']
    supported_module_operations = ['install', 'remove', 'reset']
    module_args = dict(
        type=dict(type='str', required=True, choices=supported_config_types),
        name=dict(type='str'),
        enabled=dict(type='bool', default=True),
        operation=dict(type='str', choices=supported_module_operations),
        stream=dict(type='str'),
        profile=dict(type='str'),
        set_options=dict(type='dict', default={}),
        file_path=dict(type='path'),
        dir_path=dict(type='path', default=const.YUM_REPO_DIR),
        environment_file=dict(type='path'),
        compose_url=dict(type='str'),
        centos_release=dict(type='str',
                            choices=const.COMPOSE_REPOS_RELEASES),
        arch=dict(type='str', choices=const.COMPOSE_REPOS_SUPPORTED_ARCHS,
                  default='x86_64'),
        variants=dict(type='list', default=[],
                      elements='str'),
        disable_conflicting_variants=dict(type='bool', default=False),
        disable_repos=dict(type='list', default=[],
                           elements='str'),
    )
    required_if_params = [
        ["type", "repo", ["name"]],
        ["type", "module", ["name"]],
        ["type", "enable-compose-repos", ["compose_url"]]
    ]

    module = AnsibleModule(
        argument_spec=module_args,
        required_if=required_if_params,
        supports_check_mode=False
    )

    operations_not_supp_in_py2 = ['module', 'enable-compose-repos']
    if six.PY2 and module.params['type'] in operations_not_supp_in_py2:
        msg = ("The configuration type '{0}' is not "
               "supported with python 2.").format(module.params['type'])
        module.fail_json(msg=msg)

    distro, major_version, __ = utils.get_distro_info()
    dnf_module_support = False
    for min_distro_ver in const.DNF_MODULE_MINIMAL_DISTRO_VERSIONS:
        if (distro == min_distro_ver.get('distro') and int(
                major_version) >= min_distro_ver.get('min_version')):
            dnf_module_support = True
            break
    if module.params['type'] == 'module' and not dnf_module_support:
        msg = ("The configuration type 'module' is not "
               "supported in this distro version "
               "({0}-{1}).".format(distro, major_version))
        module.fail_json(msg=msg)

    # 'set_options' expects a dict that can also contains a list of values.
    # List of elements will be converted to a comma-separated list
    m_set_opts = module.params.get('set_options')
    if m_set_opts:
        for k, v in m_set_opts.items():
            if isinstance(v, list):
                m_set_opts[k] = ','.join([str(elem) for elem in v])
            elif not isinstance(v, str):
                m_set_opts[k] = str(v)

    # Module execution
    try:
        try:
            import ansible_collections.tripleo.repos.plugins.module_utils.\
                tripleo_repos.yum_config.yum_config as cfg
        except ImportError:
            import tripleo_repos.yum_config.yum_config as cfg

        if module.params['type'] == 'repo':
            config_obj = cfg.TripleOYumRepoConfig(
                dir_path=module.params['dir_path'],
                environment_file=module.params['environment_file'])
            config_obj.add_or_update_section(
                module.params['name'],
                set_dict=m_set_opts,
                file_path=module.params['file_path'],
                enabled=module.params['enabled'])

        elif module.params['type'] == 'global':
            config_obj = cfg.TripleOYumGlobalConfig(
                file_path=module.params['file_path'],
                environment_file=module.params['environment_file'])
            config_obj.update_section('main', m_set_opts)

        elif module.params['type'] == 'enable-compose-repos':
            try:
                import ansible_collections.tripleo.repos.plugins.module_utils.\
                    tripleo_repos.yum_config.compose_repos as repos
            except ImportError:
                import tripleo_repos.yum_config.compose_repos as repos

            # 1. Create compose repo config object
            repo_obj = repos.TripleOYumComposeRepoConfig(
                module.params['compose_url'],
                module.params['centos_release'],
                dir_path=module.params['dir_path'],
                arch=module.params['arch'],
                environment_file=module.params['environment_file'])
            # 2. enable CentOS compose repos
            repo_obj.enable_compose_repos(
                variants=module.params['variants'],
                override_repos=module.params['disable_conflicting_variants'])
            # 3. Disable all repos provided in disable_repos
            for file in module.params['disable_repos']:
                repo_obj.update_all_sections(file, enabled=False)

        elif module.params['type'] == 'module':
            try:
                import ansible_collections.tripleo.repos.plugins.module_utils.\
                    tripleo_repos.yum_config.dnf_manager as dnf_mgr
            except ImportError:
                import tripleo_repos.yum_config.dnf_manager as dnf_mgr

            dnf_mod_mgr = dnf_mgr.DnfModuleManager()
            if module.params['enabled']:
                dnf_mod_mgr.enable_module(module.params['name'],
                                          stream=module.params['stream'],
                                          profile=module.params['profile'])
            else:
                dnf_mod_mgr.disable_module(module.params['name'],
                                           stream=module.params['stream'],
                                           profile=module.params['profile'])
            if module.params['operation']:
                dnf_method = getattr(dnf_mod_mgr,
                                     module.params['operation'] + "_module")
                dnf_method(module.params['name'],
                           stream=module.params['stream'],
                           profile=module.params['profile'])

    except Exception as exc:
        module.fail_json(msg=str(exc))

    # Successful module execution
    result = {
        'changed': True,
        'msg': "Yum {0} configuration was successfully updated.".format(
            module.params['type'])
    }
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
