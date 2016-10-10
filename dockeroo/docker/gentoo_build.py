
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


import re
import shutil
import tempfile

from shellescape import quote

from dockeroo import BaseGroupRecipe
from dockeroo.docker import Archive, BaseDockerSubRecipe
from dockeroo.utils import merge, string_as_bool


class DockerGentooBuildSubRecipe(BaseDockerSubRecipe): # pylint: disable=too-many-instance-attributes

    def initialize(self):
        super(DockerGentooBuildSubRecipe, self).initialize()

        base_name = re.sub(r'\W+', '_', self.name)

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
        self.build_container = "{}_build".format(base_name)
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
        self.pre_build_script_user = self.options.get('pre-build-script-user', None)
        self.pre_build_script_shell = self.options.get(
            'pre-build-script-shell', self.shell)
        self.pre_build_script = "#!{}\n{}".format(
            self.pre_build_script_shell,
            '\n'.join([f for f in [x.strip() for x in
                                   self.options.get('pre-build-script').replace('$$', '$').splitlines()]
                       if f])) if self.options.get('pre-build-script', None) is not None else None
        self.post_build_script_user = self.options.get('post-build-script-user', None)
        self.post_build_script_shell = self.options.get(
            'post-build-script-shell', self.shell)
        self.post_build_script = "#!{}\n{}".format(
            self.post_build_script_shell,
            '\n'.join([f for f in [x.strip() for x in
                                   self.options.get('post-build-script').replace('$$', '$').splitlines()]
                       if f])) if self.options.get('post-build-script', None) is not None else None
        self.assemble_container = "{}_assemble".format(base_name)
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
        self.platform = self.options.get('platform', self.engine.platform)
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
        self.expose = [y for y in [x.strip() for x in self.options.get('expose', '').splitlines()]
                       if y]
        self.volumes = [y for y in [x.strip() for x in self.options.get('volumes', '').splitlines()]
                        if y]
        self.volumes_from = self.options.get('volumes-from', None)

    def add_package_modifier(self, name, modifiers):
        for modifier in modifiers:
            slug = re.sub(r'\W+', '_', modifier.split(None, 1)[0])
            self.engine.run_cmd(
                self.build_container,
                "chroot-{arch}-docker -c \"test -f /etc/portage/package.{name} && "
                "echo {modifier} >>/etc/portage/package.{name} || "
                "mkdir -p /etc/portage/package.{name} && "
                "echo {modifier} >>/etc/portage/package.{name}/{slug}\"".format(
                    arch=self.arch, modifier=quote(modifier), slug=slug, name=name))

    def create_base_image(self, name):
        if self.archives:
            for archive in self.archives:
                archive.download(self.recipe.buildout)
            self.engine.import_archives(name, *self.archives)
        else:
            root = tempfile.mkdtemp()
            self.engine.import_path(root, name)
            shutil.rmtree(root)
        return name

    def install(self):
        if self.platform != self.engine.platform:
            if self.engine.machine is not None:
                self.engine.machine.config_binfmt(self.platform)
            else:
                raise UserError("docker-machine is not defined but binfmt configuration is needed.")
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
            if self.build_layout:
                self.engine.load_layout(self.build_container, self.build_layout)
            self.add_package_modifier('accept_keywords', self.accept_keywords)
            self.add_package_modifier('mask', self.masks)
            self.add_package_modifier('unmask', self.unmasks)
            self.add_package_modifier('use', self.uses)
            self.engine.run_cmd(
                self.build_container,
                "chroot-{arch}-docker -c \"eclean packages && emaint binhost --fix\""
                .format(arch=self.arch))
            if self.pre_build_script:
                self.engine.run_script(self.build_container, self.pre_build_script,
                                       shell=self.pre_build_script_shell, user=self.pre_build_script_user)
            if self.build_dependencies:
                self.engine.run_cmd(
                    self.build_container,
                    "env {env} chroot-{arch}-docker -c \"emerge -kb --binpkg-respect-use=y {packages}\""
                    .format(arch=self.arch, packages=' '.join(self.build_dependencies),
                            env=' '.join(['='.join(x) for x in self.build_env.items()])))
            if self.build_script:
                self.engine.run_script(self.build_container, self.build_script,
                                       shell=self.build_script_shell, user=self.build_script_user)
            if self.packages:
                self.engine.run_cmd(
                    self.build_container,
                    "env {env} chroot-{arch}-docker -c \"emerge -kb --binpkg-respect-use=y {packages}\""
                    .format(arch=self.arch, packages=' '.join(self.packages),
                            env=' '.join(['='.join(x) for x in self.build_env.items()])))
            package_atoms = ["={}".format(
                self.engine.run_cmd(
                    self.build_container,
                    "chroot-{arch}-docker -c \"equery list --format=\"\\$cpv\" {package}\" | "
                    "head -1"
                    .format(arch=self.arch, package=package),
                    quiet=True, return_output=True)) for package in self.packages]
            if package_atoms:
                self.engine.run_cmd(
                    self.build_container,
                    "chroot-{arch}-docker -c \"ROOT=/dockeroo-root emerge -OK {packages}\"".format(
                        arch=self.arch, packages=' '.join(package_atoms)))
            if self.post_build_script:
                self.engine.run_script(self.build_container, self.post_build_script,
                                       shell=self.post_build_script_shell, user=self.post_build_script_user)
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
                not next(self.engine.images(name=self.name), None):
            return self.install()
        return self.mark_completed()

    def uninstall(self):
        self.engine.remove_container(self.build_container)
        self.engine.remove_container(self.assemble_container)
        if not self.keep:
            self.engine.remove_image(self.name)


class DockerGentooBuildRecipe(BaseGroupRecipe):
    """
    This recipe builds a docker image by assembling an optional base image,
    a layout and a list of Gentoo binary packages.

    .. describe:: Usage

       The following example buildout part shows how to build a base image
       using a **builder** image produced with :py:class:`dockeroo.docker.gentoo_bootstrap.DockerGentooBootstrapRecipe`.

    .. code-block:: ini

       recipe = dockeroo:docker.gentoo-build
       layout = ${buildout:directory}/base
       use =
           sys-apps/busybox static
       accept-keywords =
           app-admin/monit **
           sys-apps/s6 **
           sys-apps/s6-rc **
           dev-lang/execline **
           dev-libs/skalibs **
       packages =
           sys-libs/ncurses:0/5
           sys-libs/ncurses:5/5
           sys-libs/readline
           sys-apps/busybox
           app-shells/bash
           sys-libs/glibc
           sys-apps/gentoo-functions
           dev-lang/execline
           dev-libs/skalibs
           sys-apps/s6
           sys-apps/s6-rc
           app-admin/monit
       shell = /bin/bash
       assemble-script =
           /bin/busybox --help | \\
           /bin/busybox sed -e '1,/^Currently defined functions:/d' \\
             -e 's/[ \\t]//g' -e 's/,$$//' -e 's/,/\\n/g' | \\
             while read a ; do
               if [ "$$a" != "" ]; then
                 /bin/busybox ln -sf "busybox" "/bin/$$a"
               fi
             done
           /sbin/ldconfig -v
           /usr/sbin/locale-gen
           /bin/s6-rc-compile /etc/s6-rc/compiled /etc/s6-rc/services
           chown 65534:65534 /var/log/s6-svscan
           rm -rf /usr/include /usr/share/doc /usr/share/info /usr/share/man
       tty = true

    .. describe:: Configuration options

       abi
           Target Application Binary Interface. Defaults to "gnu".

       accept-keywords
           Sets /etc/portage/package.accept-keywords on builder container's chrooted environment, one per line.

       arch
           Target architecture. Defaults to machine architecture.

       archives
           List of URLs of operating system initial filesystem contents for **assemble-image**.

       assemble-container
           Name of assemble container. Defaults to <partname>_assemble.

       base-image
           Name of image to use for instantiation of **assemble-container**.
           If unset, **archives** will be used to populate if available, otherwise an empty image will be created.

       build-command
          Command to launch on builder container upon creation. Defaults to "/bin/freeze".

       build-container
           Name of build container. Defaults to <partname>_build.

       build-dependencies
           List of packages to be installed in builder container's chrooted environment, but not installed
           on **assemble-container**.

       build-env
           List of environment variables to be set for packages building.

       build-image
           Name of build image. If unset, no building will be performed.

       build-layout
           Copies a local folder to **build-container**'s root with **docker cp**.

       build-script
          This shell script is executed after **build-dependencies** are built, even if no build dependencies are declared.

       build-script-shell
          Shell to use for **build-script** execution. Defaults to "/bin/sh".

       build-script-user
          User which executes the **build-script**. If unset, docker default is applied.

       build-volumes-from
          Volumes to be mounted on build container upon creation.

       command
           Sets **COMMAND** parameter on target image.

       copy
          List of extra paths to copy from builder container to assemble container,
          separated by newline. To copy directories, end pathname with path separator.
          To change destination name, append destination path on the same line, separated by space.

       expose
           Sets **EXPOSE** parameter on target image.

       keep
           Don't delete image upon uninstall.

       labels
           Sets **LABEL** parameters on target image, one per line with format KEY=VALUE.

       layout
           Copies a local folder to **assemble-container**'s root with **docker cp**.

       layout-gid
           When copying a layout onto **assemble-container**, this GID is set on destination files.

       layout-uid
           When copying a layout onto **assemble-container**, this UID is set on destination files.

       mask
           Sets /etc/portage/package.mask on builder container's chrooted environment, one per line.

       name
           Name of target image. Defaults to part name.

       packages
           List of packages to be built in builder container's chrooted environment and installed
           on **assemble-container**.

       platform
           Target platform. Defaults to machine's platform.

       pre-build-script
          This shell script is executed before building Gentoo packages.

       pre-build-script-shell
          Shell to use for **pre-build-script** execution. Defaults to "/bin/sh".

       pre-build-script-user
          User which executes the **pre-build-script**. If unset, docker default is applied.

       post-build-script
          This shell script is executed after building Gentoo packages.

       post-build-script-shell
          Shell to use for **post-build-script** execution. Defaults to "/bin/sh".

       post-build-script-user
          User which executes the **post-build-script**. If unset, docker default is applied.

       processor
           Target processor type. Defaults to machine's processor type.

       assemble-script
           Executes a shell script on **assemble-container** after installing Gentoo binary packages.

       assemble-script-shell
           Shell for **script** execution. Defaults to "/bin/sh".

       assemble-script-user
           User for **script** execution. Defaults to docker default.

       tty
           Assign a **Pseudo-TTY** to the **build-container** and **assemble-container**.

       unmask
           Sets /etc/portage/package.unmask on builder container's chrooted environment, one per line.

       use
           Sets /etc/portage/package.use on builder container's chrooted environment, one per line.

       user
           Sets **USER** parameter on target image.

       variant
           Target variant. Defaults to "dockeroo".

       volumes
           Sets **VOLUME** parameter on target image, one volume per line.

       volumes-from
           Mount volumes from specified container.
    """
    subrecipe_class = DockerGentooBuildSubRecipe
