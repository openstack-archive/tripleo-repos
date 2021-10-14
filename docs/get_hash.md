# tripleo.repos.get_hash

## What is tripleo.repos.get_hash

This utility is meant for use by TripleO deployments, particularly in zuul
continuous integration jobs. Given an [RDO named tag](https://docs.openstack.org/tripleo-docs/latest/ci/stages-overview.html#rdo-dlrn-promotion-criteria),
such as 'current-tripleo' or 'tripleo-ci-testing' it will return the hash
information, including the commit, distro and full hashes where available.

It includes a simple command line interface. If you clone the source you can
try it out of the box without installation invoking it as a module:
```
     tripleo-get-hash # by default centos8, master, current-tripleo.
     tripleo-get-hash --component tripleo --release victoria --os-version centos8
     tripleo-get-hash --release master --os-version centos7
     tripleo-get-hash --release train # by default centos8
     tripleo-get-hash --os-version rhel8 --release osp16-2 --dlrn-url http://osp-trunk.hosted.upshift.rdu2.redhat.com
     tripleo-get-hash --help
```

## Quick start

#### Install using setup.py

It is recommended to perform a user/local installation using python setup.py
to avoid the use of sudo. However you may need to set your PYTHONPATH depending
on where the python code is installed on your system.

```
python setup.py install --user
tripleo-get-hash --help
```
The tripleo-get-hash utility uses a yaml configuration file named 'config.yaml'.
If you install this utility using --user as above, the configuration file
is placed in $HOME/.local/etc/tripleo_get_hash/config.yaml (on fedora).
If this cannot be found then the config is used directly from the source directory.
When you invoke tripleo-get-hash it will tell you which config is in use:
```
$ tripleo-get-hash
2021-10-15 16:22:23,724 - tripleo-get-hash - INFO - Using config file at /home/username/.local/etc/tripleo_get_hash/config.yaml
```

#### Install using pip

You can also install using python pip - you can see the
[tripleo-get-hash module here](https://pypi.org/project/tripleo-repos/)

```
    pip install tripleo-repos --user
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

It is required that you install `tripleo.repos` collection to use the ansible
module.

See the [example playbook](https://opendev.org/openstack/tripleo-repos/src/branch/master/playbooks/example_get_hash.yaml) included here for examples of
usage. You can also test the ansible module is available and working correctly
from using shell:

```
$ ansible localhost -m tripleo.repos.get_hash -a "component=compute release=victoria"
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
