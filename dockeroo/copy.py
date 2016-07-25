
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

from dockeroo import DockerRecipe
from dockeroo.utils import merge


class Recipe(DockerRecipe):

    def __init__(self, buildout, name, options):
        super(Recipe, self).__init__(buildout, name, options)

        self.container_from = self.options['container-from']
        self.container_to = self.options['container-to']
        self.paths = [merge([None, None], y.split()[:2]) for y in [f for f in [x.strip() for x in self.options.get('paths', '').split('\n')] if f]]

    def install(self):
        for src, dst in self.paths:
            self.copy_path(self.container_from,
                           self.container_to, src, dst=dst)

    def update(self):
        pass

    def uninstall(self):
        pass
