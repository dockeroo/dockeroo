
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


from zc.buildout import UserError

from dockeroo import BaseGroupRecipe
from dockeroo.docker import BaseDockerSubRecipe, Archive
from dockeroo.utils import merge, string_as_bool


class DockerGentooBootstrapSubRecipe(BaseDockerSubRecipe): # pylint: disable=too-many-instance-attributes

    def initialize(self):
        super(DockerGentooBootstrapSubRecipe, self).initialize()
        if ':' not in self.name:
            self.name += ':latest'

        self.command = self.options.get("command", "/bin/freeze")
        self.commit = string_as_bool(self.options.get('commit', False))
        self.container = self.options.get('container',
                                          "{}_bootstrap".format(self.name.replace(':', '_')))
        self.keep = string_as_bool(self.options.get('keep', False))
        self.layout = self.options.get('layout', None)
        self.crossdev_platform = self.options.get(
            'crossdev-platform', self.machine.platform)
        sefl.build_shell = self.options.get('build-shell', self.shell)
        self.build_script = "#!{}\n{}".format(
            self.build_shell, '\n'.join([_f for _f in
                                   [x.strip() for x in
                                    self.options.get('build-script').replace('$$', '$').split('\n')]
                                   if _f])) \
                                   if self.options.get('build-script', None) is not None else None
        self.tty = string_as_bool(self.options.get('tty', False))
        self.archives = []
        for url, prefix, md5sum in [merge([None, None, None], x.split())[:3] for x in
                                    [_f for _f in
                                     [x.strip() for x in
                                      self.options.get(
                                          'archives', self.options.get('archive', '')).split('\n')]
                                     if _f]]:
            if prefix == '/':
                prefix = None
            self.archives.append(
                Archive(url=url, prefix=prefix, md5sum=md5sum))
        self.volumes = [y for y in [x.strip().split(
            ':', 1) for x in self.options.get('volumes', '').split('\n')] if y[0]]
        self.volumes_from = self.options.get('volumes-from', None)

    def install(self):
        if not any([x for x in self.images() if self.name == x['image']]):
            if not self.archives:
                raise UserError(
                    "Image does not exist and no source specified.")
            for archive in self.archives:
                archive.download(self.buildout)
            self.engine.import_archives(self.name, *self.archives)

        if not self.containers(include_stopped=True, name=self.container):
            self.engine.create_container(self.container,
                                         self.name, command=self.command,
                                         privileged=True, tty=self.tty, volumes=self.volumes,
                                         volumes_from=self.volumes_from)
        # else:
        #    raise RuntimeError("Container \"{}\" already exists".format(self.container))

        self.engine.install_freeze(self.container)

        if self.layout:
            self.engine.load_layout(self.container, self.layout)

        self.engine.start_container(self.container)

        if self.build_script:
            if self.crossdev_platform != self.machine.platform:
                self.engine.config_binfmt(self.container, self.crossdev_platform)
            self.engine.run_script(self.container, self.build_script)

        if self.commit:
            self.engine.commit_container(self.container, self.name)
            self.engine.remove_container(self.container)
            self.engine.clean_stale_images()

        return self.mark_completed()

    def update(self):
        if (self.layout and self.is_layout_updated(self.layout)) or \
            not self.engine.images(name=self.name):
            return self.install()
        return self.mark_completed()

    def uninstall(self):
        self.engine.remove_container(self.container)
        if not self.keep:
            self.engine.remove_image(self.name)


class DockerGentooBootstrapRecipe(BaseGroupRecipe):
    subrecipe_class = DockerGentooBootstrapSubRecipe
