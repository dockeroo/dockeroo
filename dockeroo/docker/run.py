
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


import os

from dockeroo import BaseGroupRecipe
from dockeroo.docker import BaseDockerSubRecipe
from dockeroo.utils import string_as_bool


class DockerRunSubRecipe(BaseDockerSubRecipe): # pylint: disable=too-many-instance-attributes

    def initialize(self):
        super(DockerRunSubRecipe, self).initialize()

        self.image = self.options['image']
        self.command = self.options.get('command', None)
        self.user = self.options.get('user', None)
        self.layout = self.options.get('layout', None)
        self.tty = string_as_bool(self.options.get('tty', False))
        self.keep = string_as_bool(self.options.get('keep', False))
        self.env = dict([y for y in [x.strip().split(
            '=') for x in self.options.get('env', '').splitlines()] if y[0]])
        self.ports = dict([y for y in [x.strip().split(
            ':') for x in self.options.get('ports', '').splitlines()] if y[0]])
        self.links = dict([y for y in [x.strip().split(
            ':') for x in self.options.get('links', '').splitlines()] if y[0]])
        self.networks = [_f for _f in
                         [x.strip() for x in self.options.get('networks', '').splitlines()]
                         if _f]
        self.network_aliases = [_f for _f in
                                [x.strip() for x in
                                 self.options.get('network-aliases', '').splitlines()]
                                if _f]
        self.volumes = [y for y in
                        [x.strip().split(':', 1) for x in
                         self.options.get('volumes', '').splitlines()]
                        if y[0]]
        self.volumes_from = self.options.get('volumes-from', None)
        self.script_shell = self.options.get('script-shell', self.shell)
        self.script_user = self.options.get('script-user', None)
        self.script = "#!{}\n{}".format(
            self.script_shell, os.linesep.join(
                [_f for _f in [x.strip() for x in
                               self.options.get('script').replace('$$', '$').splitlines()]
                 if _f])) \
                if self.options.get('script', None) is not None else None
        self.start = string_as_bool(self.options.get('start', True))

    def install(self):
        self.engine.remove_container(self.name)
        self.engine.create_container(self.name, self.image, command=self.command, run=False,
                                     tty=self.tty, volumes=self.volumes,
                                     volumes_from=self.volumes_from,
                                     user=self.user, env=self.env, ports=self.ports,
                                     networks=self.networks, links=self.links,
                                     network_aliases=self.network_aliases)
        if self.layout:
            self.engine.load_layout(self.name, self.layout)
        if not self.start:
            self.options.pop('ip-address', None)
            return self.mark_completed()
        self.engine.start_container(self.name)
        self.options['ip-address'] = self.engine.get_container_ip_address(self.name)
        if self.script:
            self.engine.run_script(self.name, self.script,
                                   shell=self.script_shell, user=self.script_user)
        return self.mark_completed()

    def update(self):
        if self.is_image_updated(self.image) or \
            not self.engine.containers(name=self.name):
            return self.install()
        if self.layout and self.is_layout_updated(self.layout):
            self.engine.load_layout(self.name, self.layout)
            if self.script:
                self.engine.run_script(self.name, self.script,
                                       shell=self.script_shell, user=self.script_user)
        return self.mark_completed()

    def uninstall(self):
        if not self.keep:
            self.engine.remove_container(self.name)


class DockerRunRecipe(BaseGroupRecipe):
    """
    This recipe executes the following tasks:

    1. Create **container** from **image** if it doesn't exist.
    2. If a **layout** is set in recipe, load it in container.
    3. Run **container**.
    4. If **script** is set, execute it on the container with **docker exec**.

    .. describe:: Usage

       The following example buildout part creates and runs a **nginx** container
       from a **nginx:latest** image.

    .. code-block:: ini

       [nginx]
       recipe = dockeroo:docker.run
       container = nginx
       image = nginx:latest

    .. describe:: Configuration options

       command
           Command to run on container. Defaults to unset.

       image
           Image to run.

       layout
           Copies a local folder to container's root with **docker cp**.

       links
           Links the container to the declared container. One per line, format is <container>:<alias>.

       machine-name
          Docker machine where **container** will be created.
          Defaults to DOCKER_MACHINE_NAME environment variable or "default" if unset.

       name
           Container name. Defaults to part name.

       networks
           Enables the selected network for the container. One per line.

       network-aliases
           Adds the defined network aliases for the container. One per line.

       script
           Executes a shell script on container upon execution.

       script-shell
           Shell for **script** execution. Defaults to "/bin/sh".

       script-user
           User for **script** execution. Defaults to docker default.

       start
           Start container after creation. Defaults to true.

       timeout
          **docker** command timeout.

       tty
           Assign a **Pseudo-TTY** to the container.

       user
           User for docker container command execution.

       volumes
           Volumes to bind mount, one per line. Format is <path>:<mountpoint>.

       volumes-from
           Mount volumes from specified container.
    """
    subrecipe_class = DockerRunSubRecipe
