# tripleo-get-hash

## What is tripleo-get-hash

This utility is meant for use by TripleO deployments, particularly in zuul
continuous integration jobs. Given an [RDO named tag](https://docs.openstack.org/tripleo-docs/latest/ci/stages-overview.html#rdo-dlrn-promotion-criteria),
such as 'current-tripleo' or 'tripleo-ci-testing' it will return the hash
information, including the commit, distro and full hashes where available.

It includes a simple command line interface. If you clone the source you can
try it out of the box without installation invoking it as a module:
```
     python -m tripleo_get_hash # by default centos8, master, current-tripleo.
     python -m tripleo_get_hash --component tripleo --release victoria --os-version centos8
     python -m tripleo_get_hash --release master --os-version centos7
     python -m tripleo_get_hash --release train # by default centos8
     python -m tripleo_get_hash --os-version rhel8 --release osp16-2 --dlrn-url http://osp-trunk.hosted.upshift.rdu2.redhat.com
     python -m tripleo_get_hash --help
```

## Quick start

#### Install using setup.py

Installation using python setup.py requires sudo, because the python source
is installed at /usr/local/lib/python.

```
sudo python setup.py install
```
The tripleo-get-hash utility uses a yaml configuration file named 'config.yaml'.
If you install this utility using setup.py as above, the configuration file
is placed in /usr/local/etc:
```
     /usr/local/etc/tripleo_get_hash/config.yaml
```

#### Install using pip

You can also install using python pip - you can see the
[tripleo-get-hash module here](https://pypi.org/project/tripleo-get-hash/)

```
    pip install tripleo-get-hash --user
```

After installation you can invoke tripleo-get-hash --help to see the various
options:
```
     tripleo-get-hash --help
```

By default this queries the delorean server at "https://trunk.rdoproject.org",
with this URL specified in config.yaml. To use a different delorean server you
can either update config.yaml or use the --dlrn-url parameter to the cli. If
instead you are instantiating TripleOHashInfo objects in code, you can create
the objects passing an existing 'config' dictionary. Note this has to contain
all of constants.CONFIG_KEYS to avoid explosions.

## Ansible Module

The tripleo-get-hash utility can be invoked from ansible using the
[tripleo_get_hash.py](https://opendev.org/openstack/tripleo-repos/src/branch/master/tripleo-get-hash/tripleo_get_hash.py) ansible module from the source tree.
If you install tripleo-get-hash using python setup.py, the module will be
installed for you at /usr/share/ansible/plugins/modules/ and is ready to use.
Otherwise you will need to copy this file to somewhere that your ansible
installation can find it. It is required that you install tripleo-get-hash either
via pip or via setup.py before you can use the ansible module.

See the [example playbook](https://opendev.org/openstack/tripleo-repos/src/branch/master/tripleo-get-hash/example_playbook.yaml) included here for examples of
usage. You can also test the ansible module is available and working correctly
from the bash shell:

```
$ ansible localhost -m tripleo_get_hash -a "component=compute release=victoria"
localhost | SUCCESS => {
    "changed": false,
    "commit_hash": "e954a56fec69637ebd671643d41bb0ecc85a2656",
    "distro_hash": "de7baf4889fba4d42ac39c9e912c42e38abb5193",
    "dlrn_url": "https://trunk.rdoproject.org/centos8-victoria/component/compute/current-tripleo/commit.yaml",
    "error": "",
    "extended_hash": "None",
    "full_hash": "e954a56fec69637ebd671643d41bb0ecc85a2656_de7baf48",
    "success": true
}
```
