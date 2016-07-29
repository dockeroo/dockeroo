
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


from zc.buildout import UserError

from dockeroo import BaseGroupRecipe
from dockeroo.docker_machine import BaseDockerMachineSubRecipe
from dockeroo.utils import string_as_bool


class DockerMachineCreateSubRecipe(BaseDockerMachineSubRecipe): # pylint: disable=too-many-instance-attributes

    def initialize(self):
        super(DockerMachineCreateSubRecipe, self).initialize()

        self.engine_driver = self.options['engine-driver']
        self.command = ['create', '-d', self.engine_driver]
        for key in [
                'engine-install-url',
                'engine-storage-driver',
            ]:
            if key in self.options:
                self.command += ["--{}".format(key), self.options.get(key)]

        for (cmd, key) in [
                ('engine-opt', 'engine-options'),
                ('engine-env', 'engine-env'),
                ('engine-label', 'engine-labels'),
                ('engine-insecure-registry', 'engine-insecure-registries'),
                ('engine-registry-mirror', 'engine-registry-mirrors'),
            ]:
            for elm in [x.strip() for x in \
                        self.options.get(key, '').splitlines()]:
                if not elm:
                    continue
                self.command += ["--{}".format(cmd), elm]

        try:
            {
                'virtualbox': self.initialize_virtualbox,
                'vmwarevsphere': self.initialize_vmwarevsphere,
            }[self.engine_driver]()
        except KeyError:
            raise UserError(
                'docker-machine driver "{}" is unknown or not supported.'
                .format(self.engine_driver))

        self.restart_if_stopped = string_as_bool(self.options.get('restart-if-stopped', True))
        self.keep = string_as_bool(self.options.get('keep', False))

    def initialize_virtualbox(self):
        for key in [
                'virtualbox-cpu-count',
                'virtualbox-memory',
                'virtualbox-host-dns-resolver',
                'virtualbox-import-boot2docker-vm',
                'virtualbox-boot2docker-url',
                'virtualbox-hostonly-cidr',
                'virtualbox-hostonly-nictype',
                'virtualbox-hostonly-nicpromisc',
            ]:
            if key in self.options:
                self.command += ["--{}".format(key), self.options.get(key)]
        for key in [
                'virtualbox-no-share',
                'virtualbox-no-dns-proxy',
                'virtualbox-no-vtx-check',
            ]:
            if key in self.options:
                self.command += ["--{}".format(key), string_as_bool(self.options.get(key))]

    def initialize_vmwarevsphere(self):
        for key in [
                'vmwarevsphere-vcenter',
                'vmwarevsphere-username',
                'vmwarevsphere-password',
            ]:
            self.command += ["--{}".format(key), self.options.get(key)]
        for key in [
                'vmwarevsphere-boot2docker-url',
                'vmwarevsphere-vcenter-port',
                'vmwarevsphere-cpu-count',
                'vmwarevsphere-memory-size',
                'vmwarevsphere-disk-size',
                'vmwarevsphere-network',
                'vmwarevsphere-datastore',
                'vmwarevsphere-datacenter',
                'vmwarevsphere-pool',
                'vmwarevsphere-hostsystem',
            ]:
            if key in self.options:
                self.command += ["--{}".format(key), self.options.get(key)]

    def install(self):
        return self.mark_completed()

    def update(self):
        return self.mark_completed()

    def uninstall(self):
        if not self.keep:
            self.remove_container(self.name)


class DockerMachineCreateRecipe(BaseGroupRecipe):
    subrecipe_class = DockerMachineCreateSubRecipe
