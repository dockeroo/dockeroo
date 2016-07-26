
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
from future import standard_library
standard_library.install_aliases()
from builtins import map
from builtins import str
from builtins import object

import base64
from copy import deepcopy
from collections import namedtuple
from datetime import datetime
from distutils.dir_util import copy_tree
from io import StringIO
import json
import logging
import os
import platform
import re
from shellescape import quote
from shutil import rmtree
import string
from subprocess import Popen, PIPE, STDOUT
import tarfile
import tempfile
import time
import tzlocal
from zc.buildout import UserError
from zc.buildout.download import Download

from dockeroo import BaseRecipe, BaseSubRecipe
from dockeroo.utils import reify, parse_datetime, random_name, string_as_bool


DEFAULT_TIMEOUT = 180

FNULL = open(os.devnull, 'w')


class DockerMachineError(RuntimeError):

    def __init__(self, msg, process):
        full_msg = "{} ({})".format(msg, process.returncode)
        err = ' '.join(process.stderr.read().splitlines())
        if err:
            full_msg = "{}: {}".format(full_msg, err)
        return super(DockerMachineError, self).__init__(full_msg)


class DockerMachineProcess(Popen):

    def __init__(self, args, stdin=None, stdout=None):
        args = ['docker-machine'] + args
        return super(DockerMachineProcess, self).__init__(
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
        p = DockerMachineProcess(['url', self.name], stdout=PIPE)
        if p.wait() != 0:
            raise DockerMachineError("Error requesting \"docker-machine url {}\"".format(self.name), p)
        return p.stdout.read().rstrip(os.linesep)

    @property
    @reify
    def inspect(self):
        p = DockerMachineProcess(['inspect', self.name], stdout=PIPE)
        if p.wait() != 0:
            raise DockerMachineError("Error requesting \"docker-machine inspect {}\"".format(self.name), p)
        return json.loads(p.stdout.read())

    @classmethod
    def machines(cls, **filters):
        SEP = '|'
        params = ['Name', 'Active', 'ActiveHost', 'ActiveSwarm', 'DriverName', 'State', 'URL',
                  'Swarm', 'Error', 'DockerVersion', 'ResponseTime']
        args = ['ls', '--format',
                SEP.join(['{{{{.{}}}}}'.format(x) for x in params])]
        for k, v in filters.items():
            args += ['-f', '{}={}'.format(k, v)]
        p = DockerMachineProcess(args, stdout=PIPE)
        if p.wait() != 0:
            raise DockerMachineError(
                "Error running \"docker-machine {}\"".format(' '.join(args)), p)
        params_map = dict([(x, re.sub(
            '((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))', r'_\1', x).lower()) for x in params])
        ret = []
        for line in p.stdout.read().splitlines():
            d = {}
            values = line.split(SEP)
            for n, param in enumerate(params):
                d[params_map[param]] = values[n] if values[
                    n] and values[n] != '<none>' else None
            ret.append(d)
        return ret

    def run_cmd(self, cmd, quiet=False, return_output=False):
        if not quiet:
            self.logger.info("Running command \"%s\" on machine \"%s\"", cmd, self.name)
        args = ['ssh', self.name, cmd]
        p = DockerMachineProcess(args, stdout=PIPE if return_output else None)
        if p.wait() != 0:
            raise DockerMachineError(
                "Error running command \"{}\" on machine \"{}\"".format(cmd, self.name), p)
        if return_output:
            return p.stdout.read().strip()
