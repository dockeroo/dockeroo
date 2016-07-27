========
dockeroo
========

dockeroo is a series of buildout_ recipes to build and manage docker containers and docker hosts.

dockeroo can build docker images from a classic Dockerfile or use a Gentoo_ container to assemble multiple Gentoo binary packages into a docker image.

.. _buildout: http://www.buildout.org/
.. _Gentoo: http://www.gentoo.org/

Useful links
============

* PyPI page: https://pypi.python.org/pypi/dockeroo/
* Code repository: https://github.com/dockeroo/dockeroo


Bug reports and Feedback
========================

Please don't hesitate to give feedback and especially report bugs or ask for new features on GitHub issue tracker:

https://github.com/dockeroo/dockeroo/issues


License
=======

Copyright © 2016, Giacomo Cariello <info@dockeroo.com>

dockeroo is released under Apache 2.0 License. See `LICENSE.rst`_ for complete license.

.. _LICENSE.rst: LICENSE.rst

Requirements
============

dockeroo requires a working buildout environment and the following system packages:

* docker >= 1.11
* docker-machine >= 0.7.0


Status
======

dockeroo is beta software.


Contents
========

dockeroo contains the following buildout recipes:

* docker.build_: creates an image from a Dockerfile.
* docker.copy_: copies files between containers.
* `docker.gentoo-bootstrap`_: builds a gentoo builder image.
* `docker.gentoo-build`_: creates an image from a gentoo builder.
* `docker.gentoo-diskimage`_: generates a disk image from a docker image.
* docker.network_: creates a docker network.
* docker.pull_: pulls an image from a registry.
* docker.push_: pushes an image to a registry.
* docker.run_: runs a docker container.
* docker.volume_: creates a docker volume.


.. _docker.build:

docker.build recipe
===================

This recipe creates a docker image by building a Dockerfile using **docker build**.

Usage
-----

The following example buildout part creates a docker image of ubuntu.

.. code-block:: ini

    [ubuntu]
    recipe = dockeroo:docker.build
    source = git@github.com:dockerfile/ubuntu.git

Configuration options
---------------------

name
    Name of the image to apply as tag. Defaults to part name.

source
    Path or URL to pass as argument to **docker build**.

build-args
    List of build arguments, one per line, expressed as KEY=VALUE.


.. _docker.copy:

docker.copy recipe
==================

This recipe copies a list of paths from a container to another.

Usage
-----

The following example buildout part copies all /lib directory and 
/bin/sh from **src** container to **dst** container. Additionally, /bin/sh
is also copied to /bin/bash on **dst** container.

.. code-block:: ini

    [copy_part]
    recipe = dockeroo:docker.copy
    container-from = src
    container-to = dst
    paths =
        /lib/
        /bin/sh
        /bin/sh /bin/bash

Configuration options
---------------------

container-from
   Source container.

container-to
   Destination container.

paths
   List of paths to copy, separated by newline. To copy directories,
   end pathname with path separator. To change destination name,
   append destination path on the same line, separated by space.


.. _docker.gentoo-bootstrap:

docker.gentoo-bootstrap recipe
==============================

This recipe creates a docker image that contains a full operating system (typically Gentoo).
Such builder image can be used to create further docker images with `docker.gentoo-build`_ recipe.

The recipe executes the following tasks:

1. Extract **archives** into a docker image.
2. Create a container from such image.
3. Install "freeze" binary into the container. This is a simple no-op binary executable.
4. If a **layout** is defined, copy layout contents onto container's root.
5. Execute **script**.
6. If **commit** is enabled, commit modifications of image.

Usage
-----

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
    script =
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

To use the above part, several other files are necessary, to be copied in via **layout**:

.. code-block::

    /etc/locale.gen
    /etc/portage/repos.conf/crossdev.conf
    /etc/portage/repos.conf/local.conf
    /usr/local/bin/chroot-x86_64-docker
    /usr/local/portage-crossdev-x86_64
    /usr/local/portage-crossdev-x86_64/metadata
    /usr/local/portage-crossdev-x86_64/metadata/layout.conf
    /usr/local/portage-crossdev-x86_64/profiles
    /usr/local/portage-crossdev-x86_64/profiles/repo_name
    /usr/x86_64-docker-linux-gnu/dockeroo-root/.keep
    /usr/x86_64-docker-linux-gnu/etc/bash/bashrc.d/emerge-chroot
    /usr/x86_64-docker-linux-gnu/etc/locale.gen
    /usr/x86_64-docker-linux-gnu/etc/portage/make.conf

Here's an example of chroot-x86_64-docker script, useful to build docker images with `docker.gentoo-build`_:

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


Configuration options
---------------------

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

image
    Name of destination image.

keep
    Don't delete image upon uninstall.

layout
    Copies a local folder to container's root with **docker cp**.

machine-name
   Docker machine where **build-image** and **base-image** reside.
   Defaults to DOCKER_MACHINE_NAME environment variable or "default" if unset.

script
    Execute this script after extraction of archives filesystem and import of layout.

timeout
   **docker** command timeout.

tty
    Assign a **Pseudo-TTY** to the container.

volumes
    Volumes to bind mount, one per line. Format is <path>:<mountpoint>.

volumes-from
    Mount volumes from specified container.


.. _docker.gentoo-build:

docker.gentoo-build recipe
==========================

This recipe builds a docker image by assembling an optional base image,
a layout and a list of Gentoo binary packages.

Usage
-----

The following example buildout part shows how to build a base image
using a **builder** image produced with `docker.gentoo-bootstrap`_.

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
    script =
        /bin/busybox --help | \
        /bin/busybox sed -e '1,/^Currently defined functions:/d' \
            -e 's/[ \t]//g' -e 's/,$$//' -e 's/,/\n/g' | \
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

Configuration options
---------------------

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
   This shell script is executed after building Gentoo packages.

build-script-shell
   Shell to use for script execution. Defaults to "/bin/sh".

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

processor
    Target processor type. Defaults to machine's processor type.

script
    Executes a shell script on **assemble-container** after installing Gentoo binary packages.

script-shell
    Shell for **script** execution. Defaults to "/bin/sh".

script-user
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


.. _docker.gentoo-diskimage:

docker.gentoo-diskimage recipe
==============================

This recipe executes the following tasks:

1. Creates a temporary container from **builder-image** docker image.
2. Executes **prepare-script** on the builder container.
3. Extracts **base-image** docker image into **build-root** folder.
4. Executes **build-script** on the builder container.
5. Extracts **image-file** from the builder container and saves it into **${:location}**.

Usage
-----

The following example buildout part shows how to build a linux disk image
from a **base** image using a **builder** image produced with `docker.gentoo-bootstrap`_.

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


Configuration options
---------------------

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

machine-name
   Docker machine where **build-image** and **base-image** reside.
   Defaults to DOCKER_MACHINE_NAME environment variable or "default" if unset.

prepare-script
   This shell script is executed before **base-image** extraction.

timeout
   **docker** command timeout.


.. _docker.network:

docker.network recipe
=====================

This recipe creates a new network if it doesn't exist.

Usage
-----

The following example buildout part creates a network named "internal_network".

.. code-block:: ini

    [internal_network]
    recipe = dockeroo:docker.network
    subnet = 10.0.0.0/8
    gateway = 10.0.0.1
    ip-range = 10.0.1.0/24
    ipv6 = true
    keep = true

Configuration options
---------------------

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


.. _docker.pull:

docker.pull recipe
==================

This recipe calls **docker pull** with appropriate parameters.
If **username** and **password** are specified, **docker login** is called prior to pulling.

Usage
-----

The following example buildout part pulls **ubuntu** image from DockerHub.

.. code-block:: ini

    [ubuntu]
    recipe = dockeroo:docker.pull
    image = ubuntu

Configuration options
---------------------

keep
    Don't delete image upon uninstall.

password
    Password for **docker login**. Defaults to unset.

machine-name
   Docker machine where **image** will be pulled to.
   Defaults to DOCKER_MACHINE_NAME environment variable or "default" if unset.

name
    Image name to pull. Use the same format as **docker pull** commandline.
    Defaults to part name.

registry
    Registry name. Defaults to DockerHub registry (index.docker.io).

username
    Username for **docker login**. Defaults to unset.

timeout
   **docker** command timeout.


.. _docker.push:

docker.push recipe
==================

This recipe calls **docker push** with appropriate parameters.
**docker login** is called prior to pushing.

Usage
-----

The following example buildout part pushes **my_image** to DockerHub.

.. code-block:: ini

    [my_image_pull]
    recipe = dockeroo:docker.push
    image = my_image
    username = my_dockerhub_username
    password = my_dockerhub_password

Configuration options
---------------------

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


.. _docker.run:

docker.run recipe
=================

This recipe executes the following tasks:

1. Create **container** from **image** if it doesn't exist.
2. If a **layout** is set in recipe, load it in container.
3. Run **container**.
4. If **script** is set, execute it on the container with **docker exec**.

Usage
-----

The following example buildout part creates and runs a **nginx** container
from a **nginx:latest** image.

.. code-block:: ini

    [nginx]
    recipe = dockeroo:docker.run
    container = nginx
    image = nginx:latest

Configuration options
---------------------

command
    Command to run on container. Defaults to unset.

image
    Image to run.

layout
    Copies a local folder to container's root with **docker cp**.

links
    Links the container to the declared container. One per line, format is <container>:<alias>.

machine-name
   Docker machine where **container** will be created.
   Defaults to DOCKER_MACHINE_NAME environment variable or "default" if unset.

name
    Container name. Defaults to part name.

networks
    Enables the selected network for the container. One per line.

network-aliases
    Adds the defined network aliases for the container. One per line.

script
    Executes a shell script on container upon execution.

script-shell
    Shell for **script** execution. Defaults to "/bin/sh".

script-user
    User for **script** execution. Defaults to docker default.

start
    Start container after creation. Defaults to true.

timeout
   **docker** command timeout.

tty
    Assign a **Pseudo-TTY** to the container.

user
    User for docker container command execution.

volumes
    Volumes to bind mount, one per line. Format is <path>:<mountpoint>.

volumes-from
    Mount volumes from specified container.


.. _docker.volume:

docker.volume recipe
====================

This recipe creates a new volume if it doesn't exist.

Usage
-----

The following example buildout part creates a volume named "distfiles_volume".

.. code-block:: ini

    [distfiles_volume]
    recipe = dockeroo:docker.volume
    keep = true

Configuration options
---------------------

machine-name
   Docker machine where **volume** will be created.
   Defaults to DOCKER_MACHINE_NAME environment variable or "default" if unset.

name
    Volume name. Defaults to part name.

keep
    Don't delete volume upon uninstall.

timeout
   **docker** command timeout.
