# tripleo.repos.yum_config

*tripleo-yum-config* utility was designed to simplify the way that TripleO
deployments manage their yum configuration. This tool helps on updating
specific configuration options for different yum configuration files like yum
repos, yum modules and yum global configuration file.

## Quick start

### Using as a python module

It is possible to use *tripleo-yum-config* as a standalone module by cloning
its repository and invoking in command line:
* **repo**

  This subcommand lets you enable or disable a repo and sets its configuration options.
  The *tripleo-yum-config* module will search for the provided repo name in all *.repo* files at REPO_DIR_PATH.
  Optionally, you can provide a dir path where your repo files live or specify the full path of the repo file.
  By default REPO_DIR_PATH is set to */etc/yum.repod.d/*.

  Examples:
  ```
  sudo python -m tripleo_yum_config repo appstream --enable --set-opts baseurl=http://newbaseurl exclude="package*"
  sudo python -m tripleo_yum_config repo epel --disable --config-dir-path=/path/to/yum.repos.d
  ```
* **module**

  This subcommand lets you enable, disable, remove, install or reset a module.
  Depending on the selected operation and module, the optional parameters 'stream' or 'profile' will also need to be provided:
  1. when enabling a module, the *stream* version will be required if the module has zero or more than one default stream.
  2. when installing a module, the *profile* will be required if the enabled stream has no default profile set.

  Examples:
  ```
  sudo tripleo-yum-config module remove tomcat
  sudo tripleo-yum-config module disable tomcat
  sudo tripleo-yum-config module enable nginx --stream mainline
  sudo tripleo-yum-config module install nginx --profile common
  ```
* **global**

  This subcommand lets you set any global yum/dnf configuration value under *[main]* section.
  If no configuration file is found by the module, a new one is created and populated.
  Optionally you can also provide the path to the configuration file.
  By default CONFIG_FILE_PATH is set to */etc/yum.conf*

  Example:
  ```
  sudo python -m tripleo_yum_config global --set-opts keepcache=1 cachedir="/var/cache/dnf"
  ```
#### Install using setup.py

Installation using python setup.py requires sudo, because the python source
is installed at /usr/local/lib/python.

```
sudo python setup.py install
```

#### Install using pip
Alternatively you can install tripleo-yum-config with python pip:
```
pip install tripleo-repos --user
```
See PyPI [tripleo-repos](https://pypi.org/project/tripleo-repos/)
project for more details.

## Usage

The utility provides a command line interface with various options. You can
invoke *tripleo-yum-config --help* to see all the available commands.
```
tripleo-yum-config --help
```

## Ansible Module

It is required that you install `tripleo.repos` collection to use the ansible
module.

An ansible module [tripleo.repos.yum_config](https://opendev.org/openstack/tripleo-repos/src/branch/master/modules/module/modules/yum_config.py)
is available for you when you install `tripleo.repos` collection.

An [example playbook](https://opendev.org/openstack/tripleo-repos/src/branch/master/playbooks/example_yum_config.yaml)
is available to assist with module usage.
