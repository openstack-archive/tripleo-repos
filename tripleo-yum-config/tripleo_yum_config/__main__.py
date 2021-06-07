
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

import tripleo_yum_config.yum_config as cfg
import tripleo_yum_config.dnf_manager as dnf_mgr


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
    cfg.TripleOYumConfig.load_logging()

    # Repo arguments
    repo_args_parser = argparse.ArgumentParser(add_help=False)
    repo_args_parser.add_argument(
        'name',
        help='name of the repo to be modified'
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
        help=(
            'set the absolute directory path that holds all repo or module '
            'configuration files')
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

    # Common file path argument
    common_parse = argparse.ArgumentParser(add_help=False)
    common_parse.add_argument(
        '--config-file-path',
        dest='config_file_path',
        help=('set the absolute file path of the configuration file to be '
              'updated')
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
        parents=[common_parse, repo_args_parser, options_parse],
        help='updates a yum repository options'
    )
    subparsers.add_parser(
        'module',
        parents=[dnf_module_parser],
        help='updates yum module options'
    )
    subparsers.add_parser(
        'global',
        parents=[common_parse, options_parse],
        help='updates global yum configuration options'
    )

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
            file_path=args.config_file_path,
            dir_path=args.config_dir_path)

        config_obj.update_section(args.name, set_dict, enable=args.enable)

    elif args.command == 'module':
        dnf_mod_mgr = dnf_mgr.DnfModuleManager()
        dnf_method = getattr(dnf_mod_mgr, args.operation + "_module")
        dnf_method(args.name, stream=args.stream, profile=args.profile)

    elif args.command == 'global':
        set_dict = options_to_dict(args.set_opts)
        config_obj = cfg.TripleOYumGlobalConfig(
            file_path=args.config_file_path)

        config_obj.update_section('main', set_dict)


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
