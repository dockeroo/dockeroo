
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
            'crossdev-platform', self.engine.platform)
        self.build_shell = self.options.get('build-shell', self.shell)
        self.build_script = "#!{}\n{}".format(
            self.build_shell,
            '\n'.join([_f for _f in
                       [x.strip() for x in
                        self.options.get('build-script').replace('$$', '$').splitlines()]
                       if _f])) \
            if self.options.get('build-script', None) is not None else None
        self.tty = string_as_bool(self.options.get('tty', False))
        self.archives = []
        for url, prefix, md5sum in [merge([None, None, None], x.split())[:3] for x in
                                    [_f for _f in
                                     [x.strip() for x in
                                      self.options.get(
                                          'archives', self.options.get('archive', '')).splitlines()]
                                     if _f]]:
            if prefix == '/':
                prefix = None
            self.archives.append(
                Archive(url=url, prefix=prefix, md5sum=md5sum))
        self.volumes = [y for y in [x.strip().split(
            ':', 1) for x in self.options.get('volumes', '').splitlines()] if y[0]]
        self.volumes_from = self.options.get('volumes-from', None)

    def install(self):
        if not any([x for x in self.engine.images() if self.name == x['image']]):
            if not self.archives:
                raise UserError(
                    "Image does not exist and no source specified.")
            for archive in self.archives:
                archive.download(self.recipe.buildout)
            self.engine.import_archives(self.name, *self.archives)

        if not self.engine.containers(include_stopped=True, name=self.container):
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
            if self.crossdev_platform != self.engine.platform:
                if self.engine.machine is not None:
                    self.engine.machine.config_binfmt(self.crossdev_platform)
                else:
                    raise UserError("docker-machine is not defined but binfmt configuration is needed.")
            self.engine.run_script(self.container, self.build_script)

        if self.commit:
            self.engine.commit_container(self.container, self.name)
            self.engine.remove_container(self.container)
            self.engine.clean_stale_images()

        return self.mark_completed()

    def update(self):
        if (self.layout and self.is_layout_updated(self.layout)) or \
            not next(self.engine.images(name=self.name), None):
            return self.install()
        return self.mark_completed()

    def uninstall(self):
        self.engine.remove_container(self.container)
        if not self.keep:
            self.engine.remove_image(self.name)


class DockerGentooBootstrapRecipe(BaseGroupRecipe):
    """
    This recipe creates a docker image that contains a full operating system (typically Gentoo).
    Such builder image can be used to create further docker images with :py:class:`dockeroo.docker.gentoo_build.DockerGentooBuildRecipe` recipe.
    
    The recipe executes the following tasks:
    
    1. Extract **archives** into a docker image.
    2. Create a container from such image.
    3. Install "freeze" binary into the container. This is a simple no-op binary executable.
    4. If a **layout** is defined, copy layout contents onto container's root.
    5. Execute **build-script**.
    6. If **commit** is enabled, commit modifications of image.
    
    .. describe:: Usage

       The following example buildout part shows how to build a full Gentoo amd64 docker image.

    .. code-block:: ini
    
       [crossdev_builder.img]
       crossdev-arch = x86_64
       crossdev-platform = x86_64
       crossdev-processor = x86_64
       crossdev-variant = docker
       crossdev-abi = gnu
       crossdev-gentoo-profile = no-multilib
       crossdev-gentoo-platform = amd64
       crossdev-gentoo-platform-flavor = amd64
       recipe = dockeroo:docker.gentoo-bootstrap
       image = dockeroo/builder_${:crossdev-arch}:latest
       container = dockeroo_builder_${:crossdev-arch}
       volumes-from = ${distfiles:container}
       gentoo-platform = amd64
       gentoo-platform-flavor = amd64-nomultilib
       gentoo-version = 20160414
       archives =
           http://distfiles.gentoo.org/releases/${:gentoo-platform}/autobuilds/${:gentoo-version}/stage3-${:gentoo-platform-flavor}-${:gentoo-version}.tar.bz2
       commit = true
       keep = true
       layout = ${buildout:containers-directory}/builder_${:crossdev-arch}
       build-script =
           test -d /usr/portage/profiles || emerge-webrsync
           emerge --sync
           emerge -uDNvkb world
           emerge -nNuvkb sys-devel/crossdev
           test -e /usr/${:crossdev-processor}-${:crossdev-variant}-linux-${:crossdev-abi}/.crossdev || \
               crossdev -S -v -t ${:crossdev-processor}-${:crossdev-variant}-linux-${:crossdev-abi} --ov-output /usr/local/portage-crossdev-${:crossdev-arch} -P -kb && \
               touch /usr/${:crossdev-processor}-${:crossdev-variant}-linux-${:crossdev-abi}/.crossdev
           (cd /usr/${:crossdev-processor}-${:crossdev-variant}-linux-${:crossdev-abi}/etc/portage && \
               rm -f make.profile && ln -s /usr/portage/profiles/default/linux/${:crossdev-gentoo-platform}/13.0/${:crossdev-gentoo-profile} make.profile)
           ROOT=/usr/${:crossdev-processor}-${:crossdev-variant}-linux-${:crossdev-abi} \
               ${:crossdev-processor}-${:crossdev-variant}-linux-${:crossdev-abi}-emerge -nuvkb1 --keep-going sys-apps/baselayout
           ROOT=/usr/${:crossdev-processor}-${:crossdev-variant}-linux-${:crossdev-abi} \
               ${:crossdev-processor}-${:crossdev-variant}-linux-${:crossdev-abi}-emerge -nuvkb1 --keep-going $(egrep '^[a-z]+' /usr/portage/profiles/default/linux/packages.build)
           ROOT=/usr/${:crossdev-processor}-${:crossdev-variant}-linux-${:crossdev-abi} \
               ${:crossdev-processor}-${:crossdev-variant}-linux-${:crossdev-abi}-emerge -nuvkb1 --keep-going sys-apps/portage sys-apps/openrc net-misc/netifrc app-portage/gentoolkit
           chroot-${:crossdev-arch}-docker -c locale-gen
           chroot-${:crossdev-arch}-docker -c env-update

    To use the above part, several other files are necessary, to be copied in via **layout**::
    
       /etc/locale.gen
       /etc/portage/repos.conf/crossdev.conf
       /etc/portage/repos.conf/local.conf
       /usr/local/bin/chroot-x86_64-docker
       /usr/local/portage-crossdev-x86_64/metadata/layout.conf
       /usr/local/portage-crossdev-x86_64/profiles/repo_name
       /usr/x86_64-docker-linux-gnu/dockeroo-root/.keep
       /usr/x86_64-docker-linux-gnu/etc/bash/bashrc.d/emerge-chroot
       /usr/x86_64-docker-linux-gnu/etc/locale.gen
       /usr/x86_64-docker-linux-gnu/etc/portage/make.conf

    Here's an example of chroot-x86_64-docker script, useful to build docker images with :py:class:`dockeroo.docker.gentoo_build.DockerGentooBuildRecipe` recipe:
    
    .. code-block:: bash
    
       #!/bin/sh
       
       cd /usr/x86_64-docker-linux-gnu
       
       set -e
       mkdir -p dev proc sys tmp etc/portage/repos.conf usr/portage usr/local/portage-crossdev-x86_64/packages var/lib/layman
       mount -o bind /dev dev
       mount -o bind /dev/pts dev/pts
       mount -o bind /dev/shm dev/shm
       mount -o bind /etc/portage/repos.conf etc/portage/repos.conf
       mount -o bind /proc proc
       mount -o bind /sys sys
       mount -o bind /tmp tmp
       mount -o bind /usr/portage usr/portage
       mount -o bind /usr/portage/distfiles usr/portage/distfiles
       mount -o bind /usr/local/portage-crossdev-x86_64 usr/local/portage-crossdev-x86_64
       mount -o bind /usr/local/portage-crossdev-x86_64/packages usr/local/portage-crossdev-x86_64/packages                                                                                         
       mount -o bind /var/lib/layman var/lib/layman                                                                                                                                                 
       cp /etc/resolv.conf etc/resolv.conf                                                                                                                                                          
       set +e                                                                                                                                                                                       
                                                                                                                                                                                                    
       chroot . /bin/bash --login "$@"                                                                                                                                                              
       ret=$?                                                                                                                                                                                       
                                                                                                                                                                                                    
       set -e                                                                                                                                                                                       
       umount var/lib/layman                                                                                                                                                                        
       umount usr/local/portage-crossdev-x86_64/packages                                                                                                                                            
       umount usr/local/portage-crossdev-x86_64                                                                                                                                                     
       umount usr/portage/distfiles                                                                                                                                                                 
       umount usr/portage                                                                                                                                                                           
       umount tmp                                                                                                                                                                                   
       umount sys                                                                                                                                                                                   
       umount proc                                                                                                                                                                                  
       umount etc/portage/repos.conf                                                                                                                                                                
       umount dev/shm                                                                                                                                                                               
       umount dev/pts                                                                                                                                                                               
       umount dev                                                                                                                                                                                   
       set +e                                                                                                                                                                                       
                                                                                                                                                                                                    
       exit $ret

    .. describe:: Configuration options

       archives
           List of URLs of operating system initial filesystem contents (Gentoo stageX).
       
       crossdev-platform
           Name of destination platform. If enabled, allows automatic configuration of QEMU binfmt mapping.
       
       command
           Command to execute upon container starting. Defaults to "/bin/freeze".
       
       commit
           Commit image changes after recipe install execution. Defaults to false.
       
       container
           Name of build container.
       
       keep
           Don't delete image upon uninstall.
       
       layout
           Copies a local folder to container's root with **docker cp**.
       
       machine-name
          Docker machine where **build-image** and **base-image** reside.
          Defaults to DOCKER_MACHINE_NAME environment variable or "default" if unset.
       
       name 
           Name of destination image. Defaults to part name.
       
       build-script
           Execute this script after extraction of archives filesystem and import of layout.
       
       timeout                                                                                                                                                                                          
          **docker** command timeout.                                                                                                                                                                   
                                                                                                                                                                                                        
       tty                                                                                                                                                                                              
           Assign a **Pseudo-TTY** to the container.                                                                                                                                                    
                                                                                                                                                                                                        
       volumes                                                                                                                                                                                          
           Volumes to bind mount, one per line. Format is <path>:<mountpoint>.                                                                                                                          
                                                                                                                                                                                                        
       volumes-from                                                                                                                                                                                     
           Mount volumes from specified container.
    """
    subrecipe_class = DockerGentooBootstrapSubRecipe
