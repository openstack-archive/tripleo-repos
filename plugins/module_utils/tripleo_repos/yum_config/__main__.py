
#   Copyright 2021 Red Hat, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

import argparse
import logging
import sys

from tripleo_repos.utils import load_logging
import tripleo_repos.yum_config.constants as const
import tripleo_repos.yum_config.yum_config as cfg
import tripleo_repos.yum_config.utils as utils


def options_to_dict(options):
    opt_dict = {}
    if options:
        for opt in options:
            try:
                k, v = opt.split('=')
            except ValueError:
                msg = 'Set options must be provided as "key=value" pairs'
                logging.error(msg)
                sys.exit(2)
            opt_dict[k] = v
    return opt_dict


def main():
    load_logging()
    # Get release model and version
    distro, major_version, __ = utils.get_distro_info()
    py_version = sys.version_info.major
    if py_version < 3:
        logging.warning("Some operations will be disabled when running with "
                        "python 2.")

    # Repo arguments
    repo_args_parser = argparse.ArgumentParser(add_help=False)
    repo_args_parser.add_argument(
        '--name',
        help='name of the repo to be modified'
    )

    environment_parse = argparse.ArgumentParser(add_help=False)
    environment_parse.add_argument(
        '--environment-file',
        dest='env_file',
        default=None,
        help=('path to an environment file to be read before creating repo '
              'files'),
    )

    parser_enable_group = repo_args_parser.add_mutually_exclusive_group()
    parser_enable_group.add_argument(
        '--enable',
        action='store_true',
        dest='enable',
        default=None,
        help='enable a yum repo or module'
    )
    parser_enable_group.add_argument(
        '--disable',
        action='store_false',
        dest='enable',
        default=None,
        help='disable a yum repo or module'
    )
    repo_args_parser.add_argument(
        '--config-dir-path',
        dest='config_dir_path',
        default=const.YUM_REPO_DIR,
        help=(
            'set the absolute directory path that holds all repo '
            'configuration files')
    )
    repo_args_parser.add_argument(
        '--down-url',
        dest='down_url',
        help=(
            'URL of a repo file to be used as base to create or update '
            'a repo configuration file.')
    )

    # Generic key-value options
    options_parse = argparse.ArgumentParser(add_help=False)
    options_parse.add_argument(
        '--set-opts',
        dest='set_opts',
        nargs='+',
        help='sets config options as key=value pairs for a specific '
             'configuration file'
    )

    # dnf module parser
    dnf_module_parser = argparse.ArgumentParser(add_help=False)
    dnf_module_parser.add_argument(
        'operation',
        choices=['enable', 'disable', 'install', 'remove', 'reset'],
        help="dnf module operation to be executed"
    )
    dnf_module_parser.add_argument(
        'name',
        help='name of the module to be modified'
    )
    dnf_module_parser.add_argument(
        '--stream',
        help="sets module stream"
    )
    dnf_module_parser.add_argument(
        '--profile',
        help="sets module profile"
    )

    # Compose repo arguments
    compose_args_parser = argparse.ArgumentParser(add_help=False)
    compose_args_parser.add_argument(
        '--compose-url',
        dest='compose_url',
        required=True,
        help='CentOS compose URL'
    )
    compose_args_parser.add_argument(
        '--release',
        dest='release',
        choices=const.COMPOSE_REPOS_RELEASES,
        default='centos-stream-8',
        help='target CentOS release.'
    )
    compose_args_parser.add_argument(
        '--arch',
        choices=const.COMPOSE_REPOS_SUPPORTED_ARCHS,
        default='x86_64',
        help='set the architecture for the destination repos.'
    )
    compose_args_parser.add_argument(
        '--disable-repos',
        nargs='+',
        help='list of repo names or repo absolute file paths to be disabled.'
    )
    compose_args_parser.add_argument(
        '--disable-all-conflicting',
        action='store_true',
        dest='disable_conflicting',
        default=False,
        help='after enabling compose repos, disable all other repos that '
             'match variant names.'
    )
    compose_args_parser.add_argument(
        '--variants',
        nargs='+',
        help='Name of the repos to be enabled. Default behavior is to enable '
             'all that match a specific release and architecture.'
    )
    compose_args_parser.add_argument(
        '--config-dir-path',
        dest='config_dir_path',
        default=const.YUM_REPO_DIR,
        help='set the absolute directory path that holds all repo '
             'configuration files'
    )

    # Common file path argument
    common_parse = argparse.ArgumentParser(add_help=False)
    common_parse.add_argument(
        '--config-file-path',
        dest='config_file_path',
        help=('set the absolute file path of the configuration file to be '
              'updated.')
    )

    # Main parser
    main_parser = argparse.ArgumentParser()
    main_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        default=False,
        help='enable verbose log level for debugging',
    )
    subparsers = main_parser.add_subparsers(dest='command')

    # Subcommands
    subparsers.add_parser(
        'repo',
        parents=[common_parse, environment_parse, repo_args_parser,
                 options_parse],
        help='updates a yum repository options'
    )
    subparsers.add_parser(
        'global',
        parents=[common_parse, environment_parse, options_parse],
        help='updates global yum configuration options'
    )

    if py_version >= 3:
        subparsers.add_parser(
            'enable-compose-repos',
            parents=[compose_args_parser, environment_parse],
            help='enable CentOS compose repos based on an compose url.'
        )

        for min_distro_ver in const.DNF_MODULE_MINIMAL_DISTRO_VERSIONS:
            if (distro == min_distro_ver.get('distro') and int(
                    major_version) >= min_distro_ver.get('min_version')):
                subparsers.add_parser(
                    'module',
                    parents=[dnf_module_parser],
                    help='updates yum module options'
                )
                break

    args = main_parser.parse_args()
    if args.command is None:
        main_parser.print_help()
        sys.exit(2)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug('Logging level set to DEBUG')

    if args.command == 'repo':
        set_dict = options_to_dict(args.set_opts)
        config_obj = cfg.TripleOYumRepoConfig(
            dir_path=args.config_dir_path,
            environment_file=args.env_file)
        if args.name is not None:
            config_obj.add_or_update_section(args.name, set_dict=set_dict,
                                             file_path=args.config_file_path,
                                             enabled=args.enable,
                                             from_url=args.down_url)
        else:
            # When no section (name) is provided, we consider all sections from
            # repo file downloaded from the URL, otherwise fail.
            if args.down_url is None:
                logging.error("You must provide a repo 'name' or a valid "
                              "'url' where repo info can be downloaded.")
                sys.exit(2)
            config_obj.add_or_update_all_sections_from_url(
                args.down_url, file_path=args.config_file_path,
                set_dict=set_dict, enabled=args.enable)

    elif args.command == 'module':
        import tripleo_repos.yum_config.dnf_manager as dnf_mgr
        dnf_mod_mgr = dnf_mgr.DnfModuleManager()
        dnf_method = getattr(dnf_mod_mgr, args.operation + "_module")
        dnf_method(args.name, stream=args.stream, profile=args.profile)

    elif args.command == 'global':
        set_dict = options_to_dict(args.set_opts)
        config_obj = cfg.TripleOYumGlobalConfig(
            file_path=args.config_file_path,
            environment_file=args.env_file)

        config_obj.update_section('main', set_dict)

    elif args.command == 'enable-compose-repos':
        import tripleo_repos.yum_config.compose_repos as compose_repos
        repo_obj = compose_repos.TripleOYumComposeRepoConfig(
            args.compose_url,
            args.release,
            dir_path=args.config_dir_path,
            arch=args.arch,
            environment_file=args.env_file)

        repo_obj.enable_compose_repos(variants=args.variants,
                                      override_repos=args.disable_conflicting)
        if args.disable_repos:
            for file in args.disable_repos:
                repo_obj.update_all_sections(file, enabled=False)


def cli_entrypoint():
    try:
        main()
        sys.exit(0)
    except KeyboardInterrupt:
        logging.info("Exiting on user interrupt")
        sys.exit(2)
    except Exception as e:
        logging.error(str(e))
        sys.exit(2)


if __name__ == "__main__":
    cli_entrypoint()
