
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


class DockerBuildSubRecipe(BaseDockerSubRecipe):

    def initialize(self):
        super(DockerBuildSubRecipe, self).initialize()

        if ':' not in self.name:
            self.name += ':latest'
        self.source = self.options['source']
        self.build_args = dict([
            y for y in [x.strip().split('=', 1)
                        for x in self.options.get('build-args', '').splitlines()] if y[0]])
        self.keep = string_as_bool(self.options.get('keep', False))

    def install(self):
        if not next(self.engine.images(self.name), None):
            self.engine.build_dockerfile(self.name,
                                         self.source,
                                         **self.build_args)
        return self.mark_completed()

    def update(self):
        return self.install()

    def uninstall(self):
        if not self.keep:
            self.engine.remove_image(self.name)


class DockerBuildRecipe(BaseGroupRecipe):
    """
    This recipe creates a docker image by building a Dockerfile using **docker build**.

    .. describe:: Usage

       The following example buildout part creates a docker image of ubuntu.

    .. code-block:: ini

       [ubuntu]
       recipe = dockeroo:docker.build
       source = git@github.com:dockerfile/ubuntu.git

    .. describe:: Configuration options

       build-args
           List of build arguments, one per line, expressed as KEY=VALUE.

       machine-name
           Docker machine where **image** will be created.
           Defaults to DOCKER_MACHINE_NAME environment variable or "default" if unset.

       keep
           Don't delete image upon uninstall.

       name
           Name of the image to apply as tag. Defaults to part name.

       source
           Path or URL to pass as argument to **docker build**.

       timeout
          **docker** command timeout.
    """
    subrecipe_class = DockerBuildSubRecipe
