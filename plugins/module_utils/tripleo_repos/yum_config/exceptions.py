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
#
#

class Base(Exception):
    """Base Exception class."""


class TripleOYumConfigNotFound(Base):
    """A configuration file was not found in the provided file path."""

    def __init__(self, error_msg):
        super(TripleOYumConfigNotFound, self).__init__(error_msg)


class TripleOYumConfigPermissionDenied(Base):
    """THh user has no permission to modify the configuration file."""

    def __init__(self, error_msg):
        super(TripleOYumConfigPermissionDenied, self).__init__(error_msg)


class TripleOYumConfigFileParseError(Base):
    """Encountered an error while parsing the configuration file."""

    def __init__(self, error_msg):
        super(TripleOYumConfigFileParseError, self).__init__(error_msg)


class TripleOYumConfigInvalidSection(Base):
    """The configuration file does not have the requested section.

    This exception is raised when the expected section in the configuration
    file does not exist and the class will not create a new one.
    """

    def __init__(self, error_msg):
        super(TripleOYumConfigInvalidSection, self).__init__(error_msg)


class TripleOYumConfigInvalidOption(Base):
    """One or more options are not valid for this configuration file."""

    def __init__(self, error_msg):
        super(TripleOYumConfigInvalidOption, self).__init__(error_msg)
