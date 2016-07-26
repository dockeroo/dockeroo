
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


class DockerVolumeSubRecipe(BaseDockerSubRecipe):

    def initialize(self):
        super(DockerVolumeSubRecipe, self).initialize()

        self.keep = string_as_bool(self.options.get('keep', False))

    def install(self):
        self.create_volume(self.name)
        return self.mark_completed()

    def update(self):
        return self.install()

    def uninstall(self):
        if not self.keep:
            self.remove_volume(self.name)


class DockerVolumeRecipe(BaseGroupRecipe):
    subrecipe_class = DockerVolumeSubRecipe
