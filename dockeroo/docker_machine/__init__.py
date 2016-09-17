
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
import json
import os
import platform
import re
from subprocess import Popen, PIPE, STDOUT

from builtins import object # pylint: disable=redefined-builtin
from future import standard_library

from dockeroo import BaseRecipe, BaseSubRecipe
from dockeroo.utils import ExternalProcessError
from dockeroo.utils import reify

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
            args += ['--filter', '{}={}'.format(key, value)]
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
            if len(values) < 2:
                continue
            for num, param in enumerate(params):
                record[params_map[param]] = values[num] \
                    if values[num] and values[num] != '<none>' else None
            ret.append(record)
        return ret

    @classmethod
    def create(cls, name, engine_driver, engine_options):
        args = ['create', '-d', engine_driver]
        for k, v in engine_options:
            args += ["--{}".format(k), v]
        args.append(name)
        proc = DockerMachineProcess(args)
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error running \"docker-machine {}\"".format(' '.join(args)), proc)

    @classmethod
    def remove(cls, name):
        args = ['rm', '-y', name]
        proc = DockerMachineProcess(args)
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error running \"docker-machine {}\"".format(' '.join(args)), proc)

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

    def config_binfmt(self, arch):
        self.run_cmd('[ -f /proc/sys/fs/binfmt_misc/register ] || '
                     'sudo mount binfmt_misc -t binfmt_misc /proc/sys/fs/binfmt_misc')
        self.run_cmd(
            '[ -f /proc/sys/fs/binfmt_misc/{arch} ] || '
            'sudo /bin/sh -c "echo \'{binfmt}\' >/proc/sys/fs/binfmt_misc/register"'.format(arch=arch, binfmt={
                'aarch64':
                    r':{arch}:M::'
                    r'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\xb7:'
                    r'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                    r'\xff\xff\xff\xff\xff\xff\xfe\xff\xff:'
                    r'/usr/bin/qemu-{arch}:',
                'arm':
                    r':{arch}:M::'
                    r'\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x28\x00:'
                    r'\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff'
                    r'\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff:'
                    r'/usr/bin/qemu-{arch}:',
                'armeb':
                    r':{arch}:M::'
                    r'\x7fELF\x01\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x28:'
                    r'\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff'
                    r'\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff:'
                    r'/usr/bin/qemu-{arch}:',
                'alpha':
                    r':{arch}:M::'
                    r'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x26\x90:'
                    r'\xff\xff\xff\xff\xff\xfe\xfe\xff\xff\xff'
                    r'\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff:'
                    r'/usr/bin/qemu-{arch}:',
                'mips':
                    r':{arch}:M::'
                    r'\x7fELF\x01\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x08:'
                    r'\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff'
                    r'\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff:'
                    r'/usr/bin/qemu-{arch}:',
                'mipsel':
                    r':{arch}:M::'
                    r'\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x08\x00:'
                    r'\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff'
                    r'\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff:'
                    r'/usr/bin/qemu-{arch}:',
                'ppc':
                    r':{arch}:M::'
                    r'\x7fELF\x01\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x14:'
                    r'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                    r'\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff:'
                    r'/usr/bin/qemu-{arch}:',
                'sh4':
                    r':{arch}:M::'
                    r'\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x2a\x00:'
                    r'\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff'
                    r'\xff\xff\xff\xff\xff\xff\xfb\xff\xff\xff:'
                    r'/usr/bin/qemu-{arch}:',
                'sh4eb':
                    r':{arch}:M::'
                    r'\x7fELF\x01\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x2a:'
                    r'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                    r'\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff:'
                    r'/usr/bin/qemu-{arch}:',
                'sparc':
                    r':{arch}:M::'
                    r'\x7fELF\x01\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x02:'
                    r'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                    r'\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff:'
                    r'/usr/bin/qemu-{arch}:',
            }[arch].format(arch=arch)))


class BaseDockerMachineSubRecipe(BaseSubRecipe):
    pass
