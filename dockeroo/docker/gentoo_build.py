
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


import shutil
import tempfile

from shellescape import quote

from dockeroo import BaseGroupRecipe
from dockeroo.docker import Archive, BaseDockerSubRecipe
from dockeroo.utils import merge, string_as_bool


class DockerGentooBuildSubRecipe(BaseDockerSubRecipe): # pylint: disable=too-many-instance-attributes

    def initialize(self):
        super(DockerGentooBuildSubRecipe, self).initialize()

        self.archives = []
        for url, prefix, md5sum in \
            [merge([None, None, None], x.split())[:3]
             for x in [f for f in
                       [x.strip() for x in \
                            self.options.get(
                                'archives', self.options.get('archive', '')).splitlines()]
                       if f]]:
            if prefix == '/':
                prefix = None
            self.archives.append(
                Archive(url=url, prefix=prefix, md5sum=md5sum))

        self.accept_keywords = [f for f in [x.strip() for x in \
            self.options.get('accept-keywords', '').splitlines()] if f]
        self.build_dependencies = [f for f in [x.strip() for x in \
            self.options.get('build-dependencies', '').splitlines()] if f]
        self.build_command = self.options.get('build-command', "/bin/freeze")
        self.build_container = "{}_build".format(self.name)
        self.build_layout = self.options.get('build-layout', None)
        self.build_image = self.options.get('build-image', None)
        self.build_env = dict([y for y in [x.strip().split(
            '=') for x in self.options.get('build-env', '').splitlines()] if y[0]])
        self.build_volumes_from = self.options.get('build-volumes-from', None)
        self.build_script_user = self.options.get('build-script-user', None)
        self.build_script_shell = self.options.get(
            'build-script-shell', self.shell)
        self.build_script = "#!{}\n{}".format(
            self.build_script_shell,
            '\n'.join([f for f in [x.strip() for x in
                                   self.options.get('build-script').replace('$$', '$').splitlines()]
                       if f])) if self.options.get('build-script', None) is not None else None

        self.assemble_container = "{}_assemble".format(self.name)
        self.copy = [merge([None, None], y.split()[:2]) for y in
                     [f for f in [x.strip() for x in self.options.get('copy', '').splitlines()]
                      if f]]
        self.base_image = self.options.get('base-image', None)
        self.keep = string_as_bool(self.options.get('keep', False))
        self.layout = self.options.get('layout', None)
        self.layout_uid = self.options.get('layout-uid', 0)
        self.layout_gid = self.options.get('layout-gid', 0)
        self.packages = [f for f in
                         [x.strip() for x in self.options.get('packages', '').splitlines()]
                         if f]
        self.platform = self.options.get('platform', self.machine.platform)
        self.arch = self.options.get('arch', self.platform)
        self.processor = self.options.get('processor', self.platform)
        self.variant = self.options.get('variant', 'dockeroo')
        self.abi = self.options.get('abi', 'gnu')

        self.assemble_script_user = self.options.get('assemble-script-user', None)
        self.assemble_script_shell = self.options.get('assemble-script-shell', self.shell)
        self.assemble_script = "#!{}\n{}".format(
            self.assemble_script_shell,
            '\n'.join([_f for _f in \
                [x.strip() for x in \
                 self.options.get('assemble-script').replace('$$', '$').splitlines()]
                       if _f])) \
            if self.options.get('assemble-script', None) is not None else None
        self.tty = string_as_bool(self.options.get('tty', False))
        self.masks = [_f for _f in [x.strip() for x in
                                    self.options.get('mask', '').splitlines()]
                      if _f]
        self.unmasks = [_f for _f in [x.strip() for x in
                                      self.options.get('unmask', '').splitlines()]
                        if _f]
        self.uses = [_f for _f in [x.strip() for x in
                                   self.options.get('use', '').splitlines()]
                     if _f]

        self.command = self.options.get('command', "/bin/freeze")
        self.user = self.options.get('user', None)
        self.labels = dict([y for y in [x.strip().split('=')
                                        for x in self.options.get('labels', '').splitlines()]
                            if y[0]])
        self.expose = [_f for _f in [x.strip() for x in self.options.get('expose', '').splitlines()]
                       if _f]
        self.volumes = [y for y in [x.strip().split(
            ':', 1) for x in self.options.get('volumes', '').splitlines()] if y[0]]
        self.volumes_from = self.options.get('volumes-from', None)

    def add_package_modifier(self, name, modifiers):
        for modifier in modifiers:
            self.engine.run_cmd(
                self.build_container,
                "chroot-{arch}-docker -c \"echo {modifier} >>/etc/portage/package.{name}\"".format(
                    arch=self.arch, modifier=quote(modifier), name=name))

    def create_base_image(self, name):
        if self.archives:
            for archive in self.archives:
                archive.download(self.buildout)
            self.engine.import_archives(name, *self.archives)
        else:
            root = tempfile.mkdtemp()
            self.engine.import_path(root, name)
            shutil.rmtree(root)
        return name

    def install(self):
        if self.base_image:
            base_image = self.base_image
        else:
            base_image = self.create_base_image(self.name)
        self.engine.remove_container(self.assemble_container)
        self.engine.create_container(self.assemble_container, base_image, command="/bin/freeze",
                                     privileged=True, tty=self.tty, volumes_from=self.volumes_from)
        self.engine.install_freeze(self.assemble_container)
        self.engine.start_container(self.assemble_container)

        if self.build_image:
            self.engine.remove_container(self.build_container)
            self.engine.create_container(self.build_container, self.build_image,
                                         command=self.build_command,
                                         privileged=True, tty=self.tty,
                                         volumes_from=self.build_volumes_from)
            self.engine.start_container(self.build_container)
            if self.platform != self.machine.platform:
                self.config_binfmt(self.build_container, self.platform)
            if self.build_layout:
                self.load_layout(self.build_container, self.build_layout)
            self.add_package_modifier('accept_keywords', self.accept_keywords)
            self.add_package_modifier('mask', self.masks)
            self.add_package_modifier('unmask', self.unmasks)
            self.add_package_modifier('use', self.uses)
            self.engine.run_cmd(
                self.build_container,
                "chroot-{arch}-docker -c \"eclean packages && emaint binhost --fix\""
                .format(arch=self.arch))
            self.engine.run_cmd(
                self.build_container,
                "env {env} chroot-{arch}-docker -c \"emerge -kb --binpkg-respect-use=y {packages}\""
                .format(arch=self.arch, packages=' '.join(self.build_dependencies + self.packages),
                        env=' '.join(['='.join(x) for x in self.build_env.items()])))
            package_atoms = ["={}".format(
                self.engine.run_cmd(
                    self.build_container,
                    "chroot-{arch}-docker -c \"equery list --format=\"\\$cpv\" {package}\" | "
                    "head -1"
                    .format(arch=self.arch, package=package),
                    quiet=True, return_output=True)) for package in self.packages]
            self.engine.run_cmd(
                self.build_container,
                "chroot-{arch}-docker -c \"ROOT=/dockeroo-root emerge -OK {packages}\"".format(
                    arch=self.arch, packages=' '.join(package_atoms)))
            if self.build_script:
                self.engine.run_script(self.build_container, self.build_script,
                                       shell=self.build_script_shell, user=self.build_script_user)
            self.engine.copy_path(self.build_container, self.assemble_container,
                                  "/usr/{processor}-{variant}-linux-{abi}/dockeroo-root/".format(
                                      processor=self.processor, variant=self.variant, abi=self.abi),
                                  dst="/")
            for src, dst in self.copy:
                self.engine.copy_path(self.build_container,
                                      self.assemble_container, src, dst=dst)
            self.engine.remove_container(self.build_container)
        if self.layout:
            self.engine.load_layout(self.assemble_container, self.layout,
                                    uid=self.layout_uid, gid=self.layout_gid)
        if self.assemble_script:
            if self.platform != self.machine.platform:
                self.engine.config_binfmt(self.assemble_container, self.platform)
            self.engine.run_script(self.assemble_container, self.assemble_script,
                                   shell=self.assemble_script_shell, user=self.assemble_script_user)
        self.engine.commit_container(self.assemble_container, self.name,
                                     command=self.command, user=self.user, labels=self.labels,
                                     expose=self.expose, volumes=self.volumes)
        self.engine.remove_container(self.assemble_container)
        self.engine.clean_stale_images()
        return self.mark_completed()

    def update(self):
        # pylint: disable=too-many-boolean-expressions
        if (self.layout and self.is_layout_updated(self.layout)) or \
            (self.build_layout and self.is_layout_updated(self.build_layout)) or \
            (self.build_image and self.is_image_updated(self.build_image)) or \
            (self.base_image and self.is_image_updated(self.base_image)) or \
                not self.engine.images(name=self.name):
            return self.install()
        return self.mark_completed()

    def uninstall(self):
        self.engine.remove_container(self.build_container)
        self.engine.remove_container(self.assemble_container)
        if not self.keep:
            self.engine.remove_image(self.name)


class DockerGentooBuildRecipe(BaseGroupRecipe):
    subrecipe_class = DockerGentooBuildSubRecipe
