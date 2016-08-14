
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


from dockeroo import BaseGroupRecipe
from dockeroo.docker import BaseDockerSubRecipe
from dockeroo.utils import merge


class DockerCopySubRecipe(BaseDockerSubRecipe):

    def initialize(self):
        super(DockerCopySubRecipe, self).initialize()

        self.container_from = self.options['container-from']
        self.container_to = self.options['container-to']
        self.paths = [merge([None, None], y.split()[:2])
                      for y in [f for f in [x.strip() for x in
                                            self.options.get('paths', '').splitlines()] if f]]

    def install(self):
        for src, dst in self.paths:
            self.engine.copy_path(self.container_from,
                                  self.container_to, src, dst=dst)

    def update(self):
        pass

    def uninstall(self):
        pass


class DockerCopyRecipe(BaseGroupRecipe):
    """
    This recipe copies a list of paths from a container to another.

    .. describe:: Usage

       The following example buildout part copies all /lib directory and
       /bin/sh from **src** container to **dst** container. Additionally, /bin/sh
       is also copied to /bin/bash on **dst** container.

    .. code-block:: ini

       [copy_part]
       recipe = dockeroo:docker.copy
       container-from = src
       container-to = dst
       paths =
           /lib/
           /bin/sh
           /bin/sh /bin/bash

    .. describe:: Configuration options

       container-from
          Source container.

       container-to
          Destination container.

       machine-name
           Docker machine where **containers** reside.
           Defaults to DOCKER_MACHINE_NAME environment variable or "default" if unset.

       paths
          List of paths to copy, separated by newline. To copy directories,
          end pathname with path separator. To change destination name,
          append destination path on the same line, separated by space.

       timeout
          **docker** command timeout.

    """
    subrecipe_class = DockerCopySubRecipe
