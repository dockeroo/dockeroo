
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016, Giacomo Cariello. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from __future__ import absolute_import
import base64
from copy import deepcopy
from collections import namedtuple
from datetime import datetime
from io import StringIO
import json
import logging
import os
import platform
import re
from shutil import rmtree
import string
from subprocess import Popen, PIPE, STDOUT
import tarfile
import tempfile
import time

from builtins import map
from builtins import str
from builtins import object
from distutils.dir_util import copy_tree
from future import standard_library
from shellescape import quote
import tzlocal
from zc.buildout import UserError
from zc.buildout.download import Download

from dockeroo import BaseRecipe, BaseSubRecipe
from dockeroo.utils import ExternalProcessError
from dockeroo.utils import reify, parse_datetime, random_name, string_as_bool

standard_library.install_aliases()

DEFAULT_TIMEOUT = 180
SEPARATOR = '|'

FNULL = open(os.devnull, 'w')


class DockerMachineProcess(Popen):

    def __init__(self, args, stdin=None, stdout=None):
        args = ['docker-machine'] + args
        super(DockerMachineProcess, self).__init__(
            args, stdin=stdin, stdout=stdout, stderr=PIPE, close_fds=True)


class DockerMachine(object):
    def __init__(self, name, logger):
        self.name = name
        self.logger = logger

    @property
    @reify
    def platform(self):
        return self.run_cmd("uname -m", quiet=True, return_output=True)

    @property
    @reify
    def url(self):
        proc = DockerMachineProcess(['url', self.name], stdout=PIPE)
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error requesting \"docker-machine url {}\"".format(self.name), proc)
        return proc.stdout.read().rstrip(os.linesep)

    @property
    @reify
    def inspect(self):
        proc = DockerMachineProcess(['inspect', self.name], stdout=PIPE)
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error requesting \"docker-machine inspect {}\"".format(self.name), proc)
        return json.loads(proc.stdout.read())

    @classmethod
    def machines(cls, **filters):
        params = ['Name', 'Active', 'ActiveHost', 'ActiveSwarm', 'DriverName', 'State', 'URL',
                  'Swarm', 'Error', 'DockerVersion', 'ResponseTime']
        args = ['ls', '--format',
                SEPARATOR.join(['{{{{.{}}}}}'.format(x) for x in params])]
        for key, value in filters.items():
            args += ['-f', '{}={}'.format(key, value)]
        proc = DockerMachineProcess(args, stdout=PIPE)
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error running \"docker-machine {}\"".format(' '.join(args)), proc)
        params_map = dict([(x, re.sub(
            '((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))', r'_\1', x).lower()) for x in params])
        ret = []
        for line in proc.stdout.read().splitlines():
            record = {}
            values = line.split(SEPARATOR)
            for num, param in enumerate(params):
                record[params_map[param]] = values[num] if values[num] and
                    values[num] != '<none>' else None
            ret.append(record)
        return ret

    def run_cmd(self, cmd, quiet=False, return_output=False):
        if not quiet:
            self.logger.info("Running command \"%s\" on machine \"%s\"", cmd, self.name)
        args = ['ssh', self.name, cmd]
        proc = DockerMachineProcess(args, stdout=PIPE if return_output else None)
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error running command \"{}\" on machine \"{}\"".format(cmd, self.name), proc)
        if return_output:
            return proc.stdout.read().strip()
