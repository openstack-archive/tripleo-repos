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
        required: false
        type: str
    enabled:
        description:
          - Change the yum repo or module to enabled or disabled.
          - This options is ignored for yum global configuration.
        required: false
        type: bool
    operation:
        description:
          - Operation to be execute within a dnf module.
        required: false
        type: str
        choices: [install, remove, reset]
    stream:
        description:
          - Sets a module stream. This options is recommended when enabling a
            module that doesn't have a default stream.
        required: false
        type: str
    profile:
        description:
          - Sets a module profile. This options is recommended when installing
            a module that doesn't have a default profile.
        required: false
        type: str
    set_options:
        description:
          - Dictionary with options to be updated. All dictionary values must
            be string or list of strings.
        required: false
        type: dict
    file_path:
        description:
          - Absolute path of the configuration file to be changed.
        required: false
        type: str
    dir_path:
        description:
          - Absolute path of the directory that contains the configuration
            file to be changed.
        required: false
        type: str

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

from ansible.module_utils.basic import AnsibleModule  # noqa: E402


def run_module():
    # define available arguments/parameters a user can pass to the module
    supported_config_types = ['repo', 'module', 'global']
    supported_module_operations = ['install', 'remove', 'reset']
    module_args = dict(
        type=dict(type='str', required=True, choices=supported_config_types),
        name=dict(type='str', required=False),
        enabled=dict(type='bool', required=False),
        operation=dict(type='str', required=False,
                       choices=supported_module_operations),
        stream=dict(type='str', required=False),
        profile=dict(type='str', required=False),
        set_options=dict(type='dict', required=False),
        file_path=dict(type='str', required=False),
        dir_path=dict(type='str', required=False),
    )

    result = dict(
        changed=False,
        msg=''
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    m_type = module.params.get('type')
    m_name = module.params.get('name')
    m_set_opts = module.params.get('set_options', {})
    m_enabled = module.params.get('enabled')
    m_file_path = module.params.get('file_path')
    m_dir_path = module.params.get('dir_path')

    # Sanity checks
    if m_type in ['repo', 'module'] and m_name is None:
        result['msg'] = (
            "The parameter 'name' is mandatory when 'type' is set to 'repo' "
            "or 'module'.")
        module.fail_json(**result)

    # 'set_options' expects a dict that can hold, as value, strings and list
    # of strings. List of strings will be converted to a comma-separated list.
    invalid_set_opts_msg = (
        "The provided value for 'set_options' parameter has an invalid "
        "format. All dict values must be string or a list of strings.")
    if m_set_opts:
        for k, v in m_set_opts.items():
            if isinstance(v, list):
                if not all(isinstance(elem, str) for elem in v):
                    result['msg'] = invalid_set_opts_msg
                    module.fail_json(**result)
                m_set_opts[k] = ','.join(v)
            elif not isinstance(v, str):
                result['msg'] = invalid_set_opts_msg
                module.fail_json(**result)

    if module.check_mode:
        # Checks were already made above
        module.exit_json(**result)

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

        if m_type == 'repo':
            config_obj = cfg.TripleOYumRepoConfig(
                file_path=m_file_path,
                dir_path=m_dir_path)
            config_obj.update_section(m_name, m_set_opts, enable=m_enabled)

        elif m_type == 'module':
            dnf_mod_mgr = dnf_mgr.DnfModuleManager()
            m_stream = module.params.get('stream')
            m_profile = module.params.get('profile')
            if m_enabled is True:
                dnf_mod_mgr.enable_module(m_name,
                                          stream=m_stream,
                                          profile=m_profile)
            elif m_enabled is False:
                dnf_mod_mgr.disable_module(m_name,
                                           stream=m_stream,
                                           profile=m_profile)
            m_operation = module.params.get('operation')
            if m_operation:
                dnf_method = getattr(dnf_mod_mgr, m_operation + "_module")
                dnf_method(m_name, stream=m_stream, profile=m_profile)

        elif m_type == 'global':
            config_obj = cfg.TripleOYumGlobalConfig(file_path=m_file_path)
            config_obj.update_section('main', m_set_opts)

    except Exception as exc:
        result['msg'] = str(exc)
        module.fail_json(**result)

    # Successful module execution
    result['changed'] = True
    result['msg'] = (
        "Yum {0} configuration was successfully updated.".format(m_type)
    )
    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
