
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
            self.engine.remove_network(self.name)


class DockerNetworkRecipe(BaseGroupRecipe):
    """
    This recipe creates a new network if it doesn't exist.
    
    .. describe:: Usage
    
       The following example buildout part creates a network named "internal_network".
    
    .. code-block:: ini
    
       [internal_network]
       recipe = dockeroo:docker.network
       subnet = 10.0.0.0/8
       gateway = 10.0.0.1
       ip-range = 10.0.1.0/24
       ipv6 = true
       keep = true
    
    .. describe:: Configuration options
    
       machine-name
          Docker machine where **network** will be created.
          Defaults to DOCKER_MACHINE_NAME environment variable or "default" if unset.
       
       gateway
           IP address of the network gateway. Auto if unset.
       
       subnet
           CIDR subnet of the network. Auto if unset.
       
       name
           Network name. Defaults to part name.
       
       internal
           Disables access to external network.
       
       ip-range
           Allocates IPs from a range.
       
       ipv6
           Enables IPv6 networking. Defaults to false.
       
       keep
           Don't delete network upon uninstall.
       
       timeout
          **docker** command timeout.
    """
    subrecipe_class = DockerNetworkSubRecipe
