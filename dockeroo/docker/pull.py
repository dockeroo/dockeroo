
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
from dockeroo.utils import string_as_bool


class DockerPullSubRecipe(BaseDockerSubRecipe):

    def initialize(self):
        super(DockerPullSubRecipe, self).initialize()

        self.username = self.options.get('username', None)
        self.password = self.options.get('password', None)
        self.registry = self.options.get('registry', 'index.docker.io')
        self.keep = string_as_bool(self.options.get('keep', False))

    def install(self):
        self.engine.pull_image(self.name,
                               username=self.username,
                               password=self.password,
                               registry=self.registry)
        return self.mark_completed()

    def update(self):
        if self.is_image_updated(self.name) or \
            not next(self.engine.images(name=self.name), None):
            return self.install()
        return self.mark_completed()

    def uninstall(self):
        if not self.keep:
            self.engine.remove_image(self.name)

class DockerPullRecipe(BaseGroupRecipe):
    """
    This recipe retrieves an image from a registry by calling **docker pull** with appropriate parameters.
    If **username** and **password** are specified, **docker login** is called prior to pulling.

    .. describe:: Usage

       The following example buildout part pulls **ubuntu** image from DockerHub.

    .. code-block:: ini

       [ubuntu]
       recipe = dockeroo:docker.pull
       image = ubuntu

    .. describe:: Configuration options

        keep
            Don't delete image upon uninstall.

        password
            Password for **docker login**. Defaults to unset.

        machine-name
           Docker machine where **image** will be pulled to.
           Defaults to DOCKER_MACHINE_NAME environment variable or "default" if unset.

        name
            Image name to pull. Use the same format as **docker pull** commandline.
            Defaults to part name.

        registry
            Registry name. Defaults to DockerHub registry (index.docker.io).

        username
            Username for **docker login**. Defaults to unset.

        timeout
           **docker** command timeout.
    """
    subrecipe_class = DockerPullSubRecipe
