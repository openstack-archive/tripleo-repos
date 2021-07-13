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
        choices: [repo, module, global]
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
'''

RETURN = r''' # '''

from ansible.module_utils.basic import AnsibleModule  # noqa: E402


def run_module():
    # define available arguments/parameters a user can pass to the module
    supported_config_types = ['repo', 'module', 'global']
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
        dir_path=dict(type='path'),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        required_if=[
            ["type", "repo", ["name"]],
            ["type", "module", ["name"]],
        ],
        supports_check_mode=False
    )

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
                tripleo_repos.yum_config.dnf_manager as dnf_mgr
            import ansible_collections.tripleo.repos.plugins.module_utils.\
                tripleo_repos.yum_config.yum_config as cfg
        except ImportError:
            import tripleo_repos.yum_config.dnf_manager as dnf_mgr
            import tripleo_repos.yum_config.yum_config as cfg

        if module.params['type'] == 'repo':
            config_obj = cfg.TripleOYumRepoConfig(
                file_path=module.params['file_path'],
                dir_path=module.params['dir_path'])
            config_obj.update_section(
                module.params['name'],
                m_set_opts,
                enable=module.params['enabled'])

        elif module.params['type'] == 'module':
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

        elif module.params['type'] == 'global':
            config_obj = cfg.TripleOYumGlobalConfig(
                file_path=module.params['file_path'])
            config_obj.update_section('main', m_set_opts)

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
