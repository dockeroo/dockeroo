
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


class DockerPushSubRecipe(BaseDockerSubRecipe):

    def initialize(self):
        super(DockerPushSubRecipe, self).initialize()

        self.username = self.options['username']
        self.password = self.options['password']
        self.registry = self.options.get('registry', 'index.docker.io')

    def install(self):
        self.engine.push_image(self.name,
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


class DockerPushRecipe(BaseGroupRecipe):
    """
    This recipe calls **docker push** with appropriate parameters.
    **docker login** is called prior to pushing.
    
    .. describe:: Usage
    
       The following example buildout part pushes **my_image** to DockerHub.
    
    .. code-block:: ini
    
       [my_image_pull]
       recipe = dockeroo:docker.push
       image = my_image
       username = my_dockerhub_username
       password = my_dockerhub_password
    
    .. describe: Configuration options
    
       name
           Image name to push. Use the same format as **docker push** commandline.
           Defaults to part name.
       
       username
           Username for **docker login**.
       
       password
           Password for **docker login**.
       
       machine-name
          Docker machine where **image** will be pushed from.
          Defaults to DOCKER_MACHINE_NAME environment variable or "default" if unset.
       
       registry
           Registry name. Defaults to DockerHub registry (index.docker.io).
       
       timeout
          **docker** command timeout.
    """
    subrecipe_class = DockerPushSubRecipe
