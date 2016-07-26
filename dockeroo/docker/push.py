
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
from shellescape import quote
import shutil
import tarfile
import tempfile

from dockeroo import BaseGroupRecipe
from dockeroo.docker import BaseDockerSubRecipe


class SubRecipe(BaseDockerSubRecipe):

    def initialize():
        super(SubRecipe, self).initialize()

        self.username = self.options['username']
        self.password = self.options['password']
        self.registry = self.options.get('registry', 'index.docker.io')

    def install(self):
        self.push_image(self.name,
                        self.username,
                        self.password,
                        registry=self.registry)
        return self.mark_completed()

    def update(self):
        if self.is_image_updated(self.name):
            return self.install()
        return self.mark_completed()

    def uninstall(self):
        pass


class Recipe(BaseGroupRecipe):
    subrecipe_class = SubRecipe
