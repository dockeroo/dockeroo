
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


class GentooDiskImageSubRecipe(BaseDockerSubRecipe): # pylint: disable=too-many-instance-attributes

    def initialize(self):
        super(GentooDiskImageSubRecipe, self).initialize()

        self.build_command = self.options.get('build-command', "/bin/freeze")
        self.build_container = "{}_build".format(self.name)
        self.build_image = self.options['build-image']
        self.build_volumes_from = self.options.get('build-volumes-from', None)
        self.build_script_user = self.options.get('build-script-user', None)
        self.build_script_shell = self.options.get(
            'build-script-shell', self.shell)
        self.prepare_script = "#!{}\n{}".format(
            self.build_script_shell, '\n'.join(
                [_f for _f in
                 [x.strip() for x in
                  self.options.get('prepare-script').replace('$$', '$').splitlines()]
                 if _f])) if self.options.get('prepare-script', None) is not None else None
        self.build_script = "#!{}\n{}".format(
            self.build_script_shell, '\n'.join(
                [_f for _f in
                 [x.strip() for x in
                  self.options.get('build-script').replace('$$', '$').splitlines()]
                 if _f])) if self.options.get('build-script', None) is not None else None
        self.build_root = self.options['build-root']
        self.base_image = self.options['base-image']
        self.image_file = self.options['image-file']

        self.platform = self.options.get('platform', self.engine.platform)
        self.arch = self.options.get('arch', self.platform)
        self.tty = string_as_bool(self.options.get('tty', False))

    def install(self):
        if self.platform != self.engine.platform:
            if self.engine.machine is not None:
                self.engine.machine.config_binfmt(self.platform)
            else:
                raise UserError("docker-machine is not defined but binfmt configuration is needed.")
        self.engine.remove_container(self.build_container)
        self.engine.create_container(self.build_container, self.build_image,
                                     command=self.build_command,
                                     privileged=True, tty=self.tty,
                                     volumes_from=self.build_volumes_from)
        self.engine.start_container(self.build_container)
        if self.prepare_script:
            self.engine.run_script(self.build_container, self.prepare_script,
                                   shell=self.build_script_shell,
                                   user=self.build_script_user)
        self.engine.copy_image_to_container(
            self.base_image, self.build_container, "/", dst=self.build_root)
        if self.build_script:
            self.engine.run_script(self.build_container, self.build_script,
                                   shell=self.build_script_shell,
                                   user=self.build_script_user)
        self.recipe.mkdir(self.location)
        self.engine.export_files(self.build_container, self.image_file, self.location)
        self.engine.remove_container(self.build_container)
        self.engine.clean_stale_images()
        return self.mark_completed()

    def update(self):
        if self.is_image_updated(self.build_image) or \
                self.is_image_updated(self.base_image):
            return self.install()
        else:
            return (self.completed, )

    def uninstall(self):
        self.engine.remove_container(self.build_container)


class DockerGentooDiskImageRecipe(BaseGroupRecipe):
    """
    This recipe executes the following tasks:

    1. Creates a temporary container from **builder-image** docker image.
    2. Executes **prepare-script** on the builder container.
    3. Extracts **base-image** docker image into **build-root** folder.
    4. Executes **build-script** on the builder container.
    5. Extracts **image-file** from the builder container and saves it into **${:location}**.

    .. describe:: Usage

       The following example buildout part shows how to build a linux disk image
       from a **base** image using a **builder** image produced with :py:class:`dockeroo.docker.gentoo_bootstrap.DockerGentooBootstrapRecipe`.

    .. code-block:: ini

        [disk-image]
        recipe = dockeroo:docker.gentoo-diskimage
        build-image = builder:latest
        base-image = base:latest
        build-root = /mnt/
        image-file = /tmp/disk.img
        prepare-script =
            mkdir -p /tmp && dd if=/dev/zero of=${:image-file} bs=1M count=2048
            parted -a optimal ${:image-file} mklabel msdos
            parted -a optimal ${:image-file} unit mib mkpart primary fat32 1 131
            parted -a optimal ${:image-file} set 1 boot on
            parted -a optimal ${:image-file} unit mib mkpart primary linux-swap 131 643
            parted -a optimal ${:image-file} unit mib mkpart primary ext2 643 100%
            rm -f /dev/loop0; mknod /dev/loop0 b 7 0
            rm -f /dev/loop0p1
            rm -f /dev/loop0p2
            rm -f /dev/loop0p3
            losetup --show -P /dev/loop0 ${:image-file}
            mknod /dev/loop0p1 b 259 0
            mknod /dev/loop0p2 b 259 1
            mknod /dev/loop0p3 b 259 2
            mkfs.vfat -F 32 -n BOOT /dev/loop0p1
            mkswap /dev/loop0p2
            mkfs.ext4 -T small /dev/loop0p3
            mount -t ext4 /dev/loop0p3 /mnt
            mkdir -p /mnt/boot
            mount -t vfat /dev/loop0p1 /mnt/boot
        build-script =
            umount /dev/loop0p1
            umount /dev/loop0p3
            losetup -d /dev/loop0 >/dev/null 2>&1

    .. describe:: Configuration options

       This recipe accepts the following options:

       base-image
          Docker image to use as base for disk creation.

       build-command
          Command to launch on builder container upon creation. Defaults to "/bin/freeze".

       build-image
          Docker image to use as builder.

       build-root
          Root folder where **base-image** is extracted.

       build-script
          This shell script is executed after **base-image** extraction.

       build-script-shell
          Shell to use for script execution. Defaults to "/bin/sh".

       build-script-user
          User which executes the **prepare-script** and **build-script**. If unset, docker default is applied.

       build-volumes-from
          Volumes to be mounted on build container upon creation.

       image-file
          Disk image file which is extracted from build container.

       location 
          Path where disk image will be saved. Defaults to ${buildout:parts-directory}/${:name}.

       machine-name
          Docker machine where **build-image** and **base-image** reside.
          Defaults to DOCKER_MACHINE_NAME environment variable or "default" if unset.

       prepare-script
          This shell script is executed before **base-image** extraction.

       timeout
          **docker** command timeout.
    """
    subrecipe_class = GentooDiskImageSubRecipe
