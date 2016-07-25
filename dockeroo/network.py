
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

        self.keep = self.options.get('keep', 'false').strip(
        ).lower() in ('true', 'yes', 'on', '1')
        self.internal = self.options.get('internal', 'false').strip(
        ).lower() in ('true', 'yes', 'on', '1')
        self.ipv6 = self.options.get('ipv6', 'false').strip(
        ).lower() in ('true', 'yes', 'on', '1')

        self.driver = self.options.get('driver', 'bridge')
        self.gateway = self.options.get('gateway', None)
        self.subnet = self.options.get('subnet', None)
        self.ip_range = self.options.get('ip-range', None)

    def install(self):
        self.create_network(self.name,
                            driver=self.driver,
                            gateway=self.gateway,
                            subnet=self.subnet,
                            ip_range=self.ip_range,
                            internal=self.internal,
                            ipv6=self.ipv6)
        return ()

    def update(self):
        pass

    def uninstall(self):
        if not self.keep:
            self.remove_network(self.name)
