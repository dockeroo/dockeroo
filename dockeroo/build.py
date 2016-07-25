
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


import time

from zc.buildout import UserError
from zc.buildout.download import Download

from dockeroo import DockerRecipe, Archive
from dockeroo.utils import merge


class Recipe(DockerRecipe):

    def __init__(self, buildout, name, options):
        super(Recipe, self).__init__(buildout, name, options)

        if ':' not in self.name:
            self.name += ':latest'
        self.source = self.options['source']
        self.build_args = dict([y for y in [x.strip().split('=', 1) for x in self.options.get('build-args', '').split('\n')] if y[0]])
        self.keep = self.options.get('keep', 'false').strip(
            ).lower() in ('true', 'yes', 'on', '1')

    def install(self):
        if not self.images(self.name):
            self.build_dockerfile(self.name,
                                  self.source,
                                  **self.build_args)
        return self.mark_completed()

    def update(self):
        return self.install()

    def uninstall(self):
        if not self.keep:
            self.remove_image(self.name)
