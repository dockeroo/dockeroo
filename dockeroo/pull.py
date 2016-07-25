
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


class Recipe(DockerRecipe):

    def __init__(self, buildout, name, options):
        super(Recipe, self).__init__(buildout, name, options)

        self.username = self.options.get('username', None)
        self.password = self.options.get('password', None)
        self.registry = self.options.get('registry', 'index.docker.io')
        self.keep = self.options.get('keep', 'false').strip(
            ).lower() in ('true', 'yes', 'on', '1')

    def install(self):
        self.pull_image(self.name,
                        username=self.username,
                        password=self.password,
                        registry=self.registry)
        return self.mark_completed()

    def update(self):
        if self.is_image_updated(self.name) or \
            not self.images(name=self.name):
            return self.install()
        return self.mark_completed()

    def uninstall(self):
        if not self.keep:
            self.remove_image(self.name)
