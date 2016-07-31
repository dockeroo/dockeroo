
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
from dockeroo.docker_machine import DockerMachine, BaseDockerMachineSubRecipe
from dockeroo.utils import string_as_bool


class DockerMachineCreateSubRecipe(BaseDockerMachineSubRecipe): # pylint: disable=too-many-instance-attributes
    """
    A recipe to create a new docker machine.

    Example:

        >>> with buildout_test(
        ... '''
        ... [buildout]
        ... parts = part
        ... find-links =
        ...     https://pypi.python.org/simple/future/
        ...     https://pypi.python.org/simple/setuptools/
        ...     https://pypi.python.org/simple/shellescape/
        ...     https://pypi.python.org/simple/tzlocal/
        ...
        ... [part]
        ... recipe = dockeroo:machine.create
        ... name = test-part
        ... engine-driver = virtualbox
        ... ''' % dict(server=server_url)) as b:
        ...    print_(b.run(), end='')
        ...    print_(b.run(), end='')
        Installing part.
        Running pre-create checks...
        Creating machine...
        (test-part) Copying <PATH> to <PATH>
        (test-part) Creating VirtualBox VM...
        (test-part) Creating SSH key...
        (test-part) Starting the VM...
        (test-part) Check network to re-create if needed...
        (test-part) Waiting for an IP...
        Waiting for machine to be running, this may take a few minutes...
        Detecting operating system of created instance...
        Waiting for SSH to be available...
        Detecting the provisioner...
        Provisioning with boot2docker...
        Copying certs to the local machine directory...
        Copying certs to the remote machine...
        Setting Docker configuration on the remote daemon...
        Checking connection to Docker...
        Docker is up and running!
        To see how to connect your Docker Client to the Docker Engine running on this virtual machine, run: docker-machine env test-part
        Updating part.
    """

    def initialize(self):
        super(DockerMachineCreateSubRecipe, self).initialize()

        self.engine_driver = self.options['engine-driver']
        self.engine_options = []
        for key in [
                'engine-install-url',
                'engine-storage-driver',
            ]:
            if key in self.options:
                self.engine_options.append((key, self.options.get(key)))

        for (opt, key) in [
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
                self.engine_options.append((opt, elm))

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
                self.engine_options.append((key, self.options.get(key)))
        for key in [
                'virtualbox-no-share',
                'virtualbox-no-dns-proxy',
                'virtualbox-no-vtx-check',
            ]:
            if key in self.options:
                self.engine_options.append((key, str(string_as_bool(self.options.get(key))).lower()))

    def initialize_vmwarevsphere(self):
        for key in [
                'vmwarevsphere-vcenter',
                'vmwarevsphere-username',
                'vmwarevsphere-password',
            ]:
            self.engine_options.append((key, self.options.get(key)))
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
                self.engine_options.append((key, self.options.get(key)))

    def install(self):
        if not DockerMachine.machines(name=self.name):
            DockerMachine.create(self.name, self.engine_driver, self.engine_options)
        return self.mark_completed()

    def update(self):
        return self.install()

    def uninstall(self):
        if not self.keep and DockerMachine.machines(name=self.name):
            DockerMachine.remove(self.name)


class DockerMachineCreateRecipe(BaseGroupRecipe):
    subrecipe_class = DockerMachineCreateSubRecipe
