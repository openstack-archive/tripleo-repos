#!/usr/bin/python
# Copyright 2021 Red Hat, Inc.
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import (absolute_import, division, print_function)


__metaclass__ = type


DOCUMENTATION = r'''
---
module: get_hash

short_description: Resolve rdo named tag to commit, full and distro hashes

version_added: "1.0.0"

description: ""

options:
    os_version:
        description: The operating system and version to fetch hashes for
        required: false
        type: str
        default: centos8
    release:
        description: The release of OpenStack you want the hash info for
        required: false
        type: str
        default: master
    component:
        description: The tripleo-ci component you are interested in
        required: false
        type: str
    tag:
        description: The named tag to fetch
        required: false
        type: str
        default: current-tripleo
    dlrn_url:
        description: The url of the DLRN server to use for hash queries
        required: false
        type: str
        default: https://trunk.rdoproject.org

author:
    - Marios Andreou (@marios)
'''

EXAMPLES = r'''
- name: Get the latest hash info for victoria centos8 tripleo component
  tripleo_get_hash:
    os_version: centos8
    release: victoria
    component: tripleo
    dlrn_url: 'https://foo.bar.baz'
'''

RETURN = r'''
full_hash:
    description: The full hash that identifies the build
    type: str
    returned: always
    sample: 'f47f1db5af04ddd1ab4cc3ccadf95884d335b3f3_92f50ace'
distro_hash:
    description: The distro hash
    type: str
    returned: when available
    sample: '92f50acecd0a218936b7163e8362e75913b62af2'
commit_hash:
    description: The commit hash
    type: str
    returned: when available
    sample: 'f47f1db5af04ddd1ab4cc3ccadf95884d335b3f3'
extended_hash:
    description: The extended hash
    type: str
    returned: when available
    sample: 'f47f1db5af04ddd1ab4cc3ccadf95884d335b3f3'
dlrn_url:
    description: The dlrn server url from which hash info was collected.
    type: str
    returned: always
    sample: 'https://trunk.rdoproject.org/centos8-master/current-tripleo/delorean.repo.md5'  # noqa E501
'''

from ansible.module_utils.basic import AnsibleModule  # noqa: E402


def run_module():
    result = dict(
        success=False,
        changed=False,
        error="",
    )

    argument_spec = dict(
        os_version=dict(type='str', required=False, default='centos8'),
        release=dict(type='str', required=False, default='master'),
        component=dict(type='str', required=False, default=None),
        tag=dict(type='str', required=False, default='current-tripleo'),
        dlrn_url=dict(type='str',
                      required=False,
                      default='https://trunk.rdoproject.org'),
    )

    module = AnsibleModule(
        argument_spec,
        supports_check_mode=False
    )

    try:

        from ansible_collections.tripleo.repos.plugins.module_utils.\
            tripleo_repos.get_hash.tripleo_hash_info import TripleOHashInfo

        os_version = module.params.get('os_version')
        release = module.params.get('release')
        component = module.params.get('component')
        tag = module.params.get('tag')
        dlrn_url = module.params.get('dlrn_url')

        hash_result = TripleOHashInfo(os_version, release, component, tag,
                                      config={'dlrn_url': dlrn_url})
        result['commit_hash'] = hash_result.commit_hash
        result['distro_hash'] = hash_result.distro_hash
        result['full_hash'] = hash_result.full_hash
        result['extended_hash'] = hash_result.extended_hash
        result['dlrn_url'] = hash_result.dlrn_url
        result['success'] = True
    except Exception as exc:
        result['error'] = str(exc)
        result['msg'] = "Error something went wrong fetching hash info"
        module.fail_json(**result)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
