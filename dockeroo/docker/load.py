
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


class DockerLoadSubRecipe(BaseDockerSubRecipe):

    def initialize(self):
        super(DockerLoadSubRecipe, self).initialize()

        self.path = self.options.get('path')
        self.keep = string_as_bool(self.options.get('keep', False))

    def install(self):
        self.engine.load_image(self.name, self.path)
        return self.mark_completed()

    def update(self):
        if self.is_image_updated(self.name) or not os.path.isfile(self.path):
            return self.install()
        return self.mark_completed()

    def uninstall(self):
        if not self.keep:
            self.engine.remove_image(self.name)

class DockerLoadRecipe(BaseGroupRecipe):
    """
    This recipe loads an image from a file by calling **docker load** with appropriate parameters.

    .. describe:: Usage

       The following example buildout part loads **ubuntu** image from ubuntu.img.

    .. code-block:: ini

       [ubuntu]
       recipe = dockeroo:docker.load
       path = ${buildout:directory}/ubuntu.img.

    .. describe:: Configuration options

        keep
            Don't remove image upon uninstall.

        name
            Image name to save. Use the same format as **docker save** commandline.
            Defaults to part name.

        timeout
           **docker** command timeout.
    """
    subrecipe_class = DockerLoadSubRecipe
