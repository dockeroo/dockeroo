
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


class DockerNetworkSubRecipe(BaseDockerSubRecipe):

    def initialize(self):
        super(DockerNetworkSubRecipe, self).initialize()

        self.keep = string_as_bool(self.options.get('keep', False))
        self.internal = string_as_bool(self.options.get('internal', False))
        self.ipv6 = string_as_bool(self.options.get('ipv6', False))

        self.driver = self.options.get('driver', 'bridge')
        self.gateway = self.options.get('gateway', None)
        self.subnet = self.options.get('subnet', None)
        self.ip_range = self.options.get('ip-range', None)

    def install(self):
        self.engine.create_network(self.name,
                                   driver=self.driver,
                                   gateway=self.gateway,
                                   subnet=self.subnet,
                                   ip_range=self.ip_range,
                                   internal=self.internal,
                                   ipv6=self.ipv6)
        return self.mark_completed()

    def update(self):
        if not self.engine.networks(name=self.name):
            return self.install()
        return self.mark_completed()

    def uninstall(self):
        if not self.keep:
            self.remove_network(self.name)


class DockerNetworkRecipe(BaseGroupRecipe):
    subrecipe_class = DockerNetworkSubRecipe
