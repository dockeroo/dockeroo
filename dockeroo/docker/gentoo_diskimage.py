
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


class SubRecipe(BaseDockerSubRecipe):

    def initialize(self):
        super(SubRecipe, self).initialize()

        self.build_command = self.options.get('build-command', "/bin/freeze")
        self.build_container = "{}_build".format(self.name)
        self.build_image = self.options['build-image']
        self.build_volumes_from = self.options.get('build-volumes-from', None)
        self.build_script_user = self.options.get('build-script-user', None)
        self.build_script_shell = self.options.get(
            'build-script-shell', self.shell)
        self.prepare_script = "#!{}\n{}".format(self.build_script_shell,
                                                '\n'.join([_f for _f in [x.strip() for x in self.options.get('prepare-script').replace('$$', '$').split('\n')] if _f])) if self.options.get('prepare-script', None) is not None else None
        self.build_script = "#!{}\n{}".format(self.build_script_shell,
                                              '\n'.join([_f for _f in [x.strip() for x in self.options.get('build-script').replace('$$', '$').split('\n')] if _f])) if self.options.get('build-script', None) is not None else None
        self.build_root = self.options['build-root']
        self.base_image = self.options['base-image']
        self.image_file = self.options['image-file']

        self.platform = self.options.get('platform', self.machine.platform)
        self.arch = self.options.get('arch', self.platform)
        self.tty = string_as_bool(self.options.get('tty', False))

    def install(self):
        self.location = self.options.get("location", os.path.join(
            self.buildout["buildout"]["parts-directory"], self.name))
        self.remove_container(self.build_container)
        self.create_container(self.build_container, self.build_image, command=self.build_command,
                              privileged=True, tty=self.tty, volumes_from=self.build_volumes_from)
        self.start_container(self.build_container)
        if self.platform != self.machine.platform:
            self.config_binfmt(self.build_container, self.platform)
        if self.prepare_script:
            self.run_script(self.build_container, self.prepare_script,
                            shell=self.build_script_shell, user=self.build_script_user)
        self.copy_image_to_container(
            self.base_image, self.build_container, "/", dst=self.build_root)
        if self.build_script:
            self.run_script(self.build_container, self.build_script,
                            shell=self.build_script_shell, user=self.build_script_user)
        self.export_files(self.build_container, self.image_file, self.location)
        self.remove_container(self.build_container)
        self.clean_stale_images()
        return self.mark_completed()

    def update(self):
        if self.is_image_updated(self.build_image) or \
                self.is_image_updated(self.base_image):
            return self.install()
        else:
            return (self.completed, )

    def uninstall(self):
        self.remove_container(self.build_container)


class Recipe(BaseGroupRecipe):
    subrecipe_class = SubRecipe
