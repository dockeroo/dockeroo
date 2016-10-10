
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


from __future__ import absolute_import
from copy import deepcopy
from datetime import datetime
import logging
import os
import platform
import re
from shutil import rmtree
from subprocess import Popen, PIPE, STDOUT
import tarfile
import tempfile
import time

from builtins import map # pylint: disable=redefined-builtin
from builtins import str # pylint: disable=redefined-builtin
from builtins import object # pylint: disable=redefined-builtin
from distutils.dir_util import copy_tree
from future import standard_library
import tzlocal
from zc.buildout import UserError
from zc.buildout.download import Download

from dockeroo import BaseRecipe, BaseSubRecipe
from dockeroo.docker_machine import DockerMachine
from dockeroo.utils import ExternalProcessError
from dockeroo.utils import reify, parse_datetime, random_name, listify

standard_library.install_aliases()

DEFAULT_TIMEOUT = 180

FNULL = open(os.devnull, 'w')

SEPARATOR = '|'


class Archive(object):

    def __init__(self, url=None, path=None, prefix=None, md5sum=None):
        self.url = url
        self.path = path
        self.prefix = prefix
        self.md5sum = md5sum

    def download(self, buildout):
        download = Download(buildout['buildout'], hash_name=False)
        self.path, _ = download(self.url, md5sum=self.md5sum)

    def __repr__(self):
        return self.url or self.path


class DockerProcess(Popen):

    def __init__(self, engine, args, stdin=None, stdout=None, stderr=PIPE, env=None, config=None):
        self.engine = engine
        args = ['docker'] + args
        if config is not None:
            args = ['--config', config] + args
        custom_env = os.environ.copy()
        custom_env.update(engine.client_environment)
        custom_env.update(env or {})
        self.engine.logger.debug("Running command: %s", ' '.join(args))
        super(DockerProcess, self).__init__(
            args, stdin=stdin, stdout=stdout, stderr=stderr, close_fds=True, env=custom_env)


class DockerRegistryLogin(object): # pylint: disable=too-few-public-methods

    def __init__(self, engine, registry, username, password):
        self.engine = engine
        self.registry = "https://{}/v1/".format(registry)
        self.username = username
        self.password = password
        self.config_path = None

    def __enter__(self):
        self.config_path = tempfile.mkdtemp()
        proc = DockerProcess(self.engine,
                             ['login', '-u', self.username, '-p', self.password, self.registry],
                             config=self.config_path)
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error requesting \"docker login {}\"".format(self.registry), proc)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        rmtree(self.config_path)


class DockerEngine(object): # pylint: disable=too-many-public-methods

    def __init__(self, logger=None, url=None, tlsverify=None, tlscertpath=None, machine_name=None,
                 shell='/bin/sh', timeout=DEFAULT_TIMEOUT):
        self.logger = logger or logging.getLogger(__name__)
        self.shell = shell
        self.timeout = timeout
        self._tlscertpath = tlscertpath
        self._tlsverify = tlsverify
        self._url = url

        if machine_name is None:
            machine_name = os.environ.get('DOCKER_MACHINE_NAME', None)
        if machine_name is not None:
            self.machine = DockerMachine(machine_name, logger=self.logger)
        else:
            if DockerMachine.machines(name='default'):
                self.machine = DockerMachine('default', logger=self.logger)
            else:
                self.machine = None

    @property
    @reify
    def client_environment(self):
        """
        Example:

            >>> dm = DockerEngine(machine_name='default')
            >>> 'DOCKER_TLS_VERIFY' in dm.client_environment
            True
            >>> 'DOCKER_HOST' in dm.client_environment
            True
            >>> 'DOCKER_CERT_PATH' in dm.client_environment
            True
            >>> 'DOCKER_MACHINE_NAME' in dm.client_environment
            True
            >>> dm.client_environment['DOCKER_MACHINE_NAME'] == dm.machine.name
            True
        """
        env = {
            'DOCKER_HOST': self.url,
            'DOCKER_TLS_VERIFY': str(int(self.tlsverify)),
            'DOCKER_CERT_PATH': self.tlscertpath,
        }
        if self.machine is not None:
            env['DOCKER_MACHINE_NAME'] = self.machine.name
        return env

    @property
    @reify
    def client_version(self):
        r"""
        Example:

            >>> dm = DockerEngine(machine_name='default')
            >>> bool(re.search(r'^\d+.\d+.\d+$', dm.client_version))
            True
        """
        proc = DockerProcess(self, ['version', '-f', '{{.Client.Version}}'], stdout=PIPE)
        if proc.wait() != 0:
            raise ExternalProcessError("Error requesting version", proc)
        return proc.stdout.read().rstrip(os.linesep)

    @property
    @reify
    def platform(self):
        """
        Example:

            >>> dm = DockerEngine(machine_name='default')
            >>> dm.platform in (
            ...     'arm', 'armv4', 'armv4t', 'armv5te', 'armv6j', 'armv7a',
            ...     'hppa', 'hppa1.1', 'hppa2.0', 'hppa64',
            ...     'i386', 'i486', 'i586', 'i686',
            ...     'ia64',
            ...     'm68k',
            ...     'mips', 'mips64',
            ...     'powerpc', 'powerpc64',
            ...     's390',
            ...     'sh', 'sh4', 'sh64',
            ...     'sparc', 'sparc64',
            ...     'x86_64')
            True
        """
        if self.machine is not None:
            return self.machine.platform
        proc = DockerProcess(self, ['info'], stdout=PIPE)
        if proc.wait() != 0:
            raise ExternalProcessError("Error requesting info", proc)
        result = proc.stdout.read().splitlines()
        return [l for l in result if l.startswith('Architecture: ')][0].split(': ')[1]

    @property
    @reify
    def url(self):
        """
        Example:

            >>> dm = DockerEngine(machine_name='default')
            >>> dm.url.startswith('tcp://')
            True
        """
        if self._url is not None:
            return self._url
        elif self.machine is not None:
            return self.machine.url
        else:
            return None

    @property
    @reify
    def tlsverify(self):
        if self._tlsverify is not None:
            return self._tlsverify
        elif self.machine is not None:
            return self.machine.inspect['HostOptions']['EngineOptions']['TlsVerify']
        else:
            return None

    @property
    @reify
    def tlscertpath(self):
        if self._tlscertpath is not None:
            return self._tlscertpath
        elif self.machine is not None:
            return self.machine.inspect['HostOptions']['AuthOptions']['StorePath'].encode('utf-8')
        else:
            return None

    def build_dockerfile(self, tag, path, **kwargs):
        self.logger.info("Building Dockerfile from context \"%s\"", path)
        args = ['build', '-t', tag]
        for key, value in kwargs.items():
            args += ['--build-arg', '{}={}'.format(key, value)]
        args.append(path)
        proc = DockerProcess(self, args)
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error building Dockerfile from context \"{}\"".format(path), proc)

    def clean_stale_images(self):
        for image in self.images(dangling='true'):
            self.remove_image(image['image'])
        for image in self.images('<none>'):
            self.remove_image(image['image'])

    def commit_container(self, container, image, command=None, user=None,
                         labels=None, expose=None, volumes=None):
        self.logger.info(
            "Committing container \"%s\" to image \"%s\"", container, image)
        args = ['commit']
        if command:
            args.append(
                "--change='CMD [{}]'".format(', '.join(
                    ['"{}"'.format(x) for x in command.split()])))
        if user:
            args.append("--change='USER \"{}\"'".format(user))
        for key, value in (labels or {}).items():
            args.append("--change='LABEL \"{}\"=\"{}\"".format(key, value))
        for port in expose or []:
            args.append("--change='EXPOSE {}'".format(port))
        for volume in volumes or []:
            args.append("--change='VOLUME {}'".format(volume))
        args += [container, image]
        proc = DockerProcess(self, args, stdout=FNULL)
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error committing container \"{}\"".format(container), proc)

    @listify
    def containers(self, include_stopped=False, **filters):
        params = ['ID', 'Image', 'Command', 'CreatedAt', 'RunningFor',
                  'Ports', 'Status', 'Size', 'Names', 'Labels', 'Mounts']
        args = ['ps', '--format',
                SEPARATOR.join(['{{{{.{}}}}}'.format(x) for x in params])]
        if include_stopped:
            args.append('-a')
        for key, value in filters.items():
            args += ['-f', '{}={}'.format(key, value)]
        proc = DockerProcess(self, args, stdout=PIPE)
        for line in proc.stderr.read().splitlines():
            self.logger.error(line)
        proc.wait()
        params_map = dict([(x, re.sub(
            '((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))', r'_\1', x).lower()) for x in params])
        for line in proc.stdout.read().splitlines():
            container = {}
            values = line.split(SEPARATOR)
            for num, param in enumerate(params):
                if param in ['Labels', 'Mounts', 'Names', 'Ports']:
                    container[params_map[param]] = values[num].split(',') if values[num] else []
                    if param == 'Labels':
                        container[params_map[param]] = [tuple(
                            x.split('=')) for x in container[params_map[param]]]
                    elif param == 'Ports':
                        container[params_map[param]] = [tuple(
                            x.split('->')) for x in container[params_map[param]]]
                elif param == 'Status':
                    container[params_map[param]] = {
                        'created': 'created',
                        'dead': 'dead',
                        'exited': 'exited',
                        'paused': 'paused',
                        'restarting': 'restarting',
                        'up': 'running',
                    }[values[num].split(' ')[0].lower()]
                elif param == 'CreatedAt':
                    container[params_map[param]] = parse_datetime(values[num]).astimezone(
                        tzlocal.get_localzone()).replace(tzinfo=None)
                else:
                    container[params_map[param]] = values[num] if values[num] else None
            yield container

    def copy_image_to_container(self, image, container, src, dst):
        tmp = random_name()
        self.create_container(tmp, image)
        self.copy_path(tmp, container, src, dst=dst, dst_exec=True)
        self.remove_container(tmp)

    def copy_layout(self, src, dst):
        self.logger.info("Copying layout \"%s\" on \"%s\"", src, dst)
        return copy_tree(src, dst)

    def copy_path(self, container_src, container_dst, src, dst=None, dst_exec=False, processor=None):
        if dst is None:
            dst = os.path.join(*os.path.dirname(src).split(os.sep))
        if processor is None:
            processor = lambda x: x
        self.logger.info("Copying files from container \"%s:%s\" to container \"%s:%s\"",
                         container_src, src, container_dst, dst)
        if src.endswith('/'):
            src_prefix = os.path.dirname(src).split(os.sep)[-1] + '/'
        else:
            src_prefix = ''

        def layout_filter(obj):
            if dst is not None:
                if len(obj.name) > len(src_prefix):
                    obj.name = os.path.join(dst, obj.name[len(src_prefix):])
                else:
                    obj.name = dst
                if obj.type == tarfile.LNKTYPE:
                    if len(obj.linkname) > len(src_prefix):
                        obj.linkname = os.path.join(
                            dst, obj.linkname[len(src_prefix):])
                    else:
                        obj.linkname = dst
            return obj
        p_in = DockerProcess(self, ['cp', "{}:{}".format(
            container_src, src), "-"], stdout=PIPE)
        if dst_exec:
            p_out = DockerProcess(self, ['exec', '-i', container_dst, "tar", "-xpf",
                                         "-", "-C", "/"], stdin=PIPE)
        else:
            p_out = DockerProcess(self, ['cp', "-", "{}:/".format(container_dst)], stdin=PIPE)
        tar_in = tarfile.open(fileobj=p_in.stdout, mode='r|')
        tar_out = tarfile.open(fileobj=p_out.stdin, mode='w|')
        for tarinfo in tar_in:
            tarinfo = processor(layout_filter(tarinfo))
            if tarinfo is None:
                continue
            if tarinfo.isreg():
                tar_out.addfile(tarinfo, fileobj=tar_in.extractfile(tarinfo))
            else:
                tar_out.addfile(tarinfo)
        tar_in.close()
        tar_out.close()
        p_in.stdout.close()
        p_out.stdin.close()
        if p_in.wait() != 0:
            raise ExternalProcessError(
                "Error processing path on container \"{}\"".format(container_src), p_in)
        if p_out.wait() != 0:
            raise ExternalProcessError(
                "Error processing path on container \"{}\"".format(container_dst), p_out)

    def create_container(self, container, image, command=None, privileged=False, run=False, # pylint: disable=too-many-arguments,too-many-locals,too-many-branches
                         tty=False, volumes=None, volumes_from=None, user=None, networks=None,
                         links=None, network_aliases=None, env=None, ports=None):
        if not any([x for x in self.containers(include_stopped=True) if container in x['names']]):
            self.logger.info("Creating container \"%s\"", container)
            args = ['create', '--name="{}"'.format(container)]
            for key, value in (env or {}).items():
                args += ['-e', "{}={}".format(key, value)]
            for key, value in (ports or {}).items():
                args += ['-p', "{}:{}".format(key, value)]
            for key, value in (links or {}).items():
                args += ['--link', "{}:{}".format(key, value)]
            for network in networks or []:
                args += ['--network', network]
            for network_alias in network_aliases or []:
                args += ['--network-alias', network_alias]
            if privileged:
                args.append('--privileged')
            if tty:
                args.append('--tty')
            if user:
                args += ['-u', user]
            if volumes:
                args += ["--volume={}:{}".format(key, value) for key, value in volumes]
            if volumes_from:
                args.append("--volumes-from={}".format(volumes_from))
            args.append(image)
            if command:
                args += command.split(" ")
            proc = DockerProcess(self, args, stdout=FNULL)
            if proc.wait() != 0:
                raise ExternalProcessError(
                    "Error creating container \"{}\"".format(container), proc)
        if run:
            self.start_container(container)

    def create_network(self, network, driver='bridge', gateway=None, subnet=None,
                       ip_range=None, ipv6=False, internal=False):
        self.logger.info("Creating network \"%s\"", network)
        args = ['network', 'create', '-d', driver]
        if gateway is not None:
            args += ['--gateway', gateway]
        if ip_range is not None:
            args += ['--ip-range', ip_range]
        if subnet is not None:
            args += ['--subnet', subnet]
        if ipv6:
            args.append('--ipv6')
        if internal:
            args.append('--internal')
        args.append(network)
        proc = DockerProcess(self, args)
        if proc.wait() != 0:
            raise ExternalProcessError("Error creating network \"{}\"".format(network), proc)

    def create_volume(self, volume):
        if self.volumes(name=volume):
            return
        self.logger.info("Creating volume \"%s\"", volume)
        args = ['volume', 'create', '--name="{}"'.format(volume)]
        proc = DockerProcess(self, args, stdout=FNULL)
        if proc.wait() != 0:
            raise ExternalProcessError("Error creating volume \"{}\"".format(volume), proc)

    def export_files(self, container, src, dst):
        self.logger.info(
            "Export files from \"%s:%s\" to path \"%s\"", container, src, dst)
        args = ['cp', "{}:{}".format(container, src), "-"]
        proc = DockerProcess(self, args, stdout=PIPE)
        tar = tarfile.open(fileobj=proc.stdout, mode='r|')
        for fin in tar:
            if not fin.isreg():
                continue
            fout = open(os.path.join(dst, os.path.basename(fin.name)), 'w')
            fout.write(tar.extractfile(fin).read())
            fout.close()
        tar.close()
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error exporting files from container \"{}\"".format(container), proc)

    def get_container_ip_address(self, container):
        args = ['inspect', '--format="{{.NetworkSettings.IPAddress}}"', container]
        proc = DockerProcess(self, args, stdout=PIPE)
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error requesting \"docker inspect {}\"".format(container), proc)
        return proc.stdout.read().rstrip(os.linesep)

    def images(self, name=None, **filters):
        params = ['ID', 'Repository', 'Tag', 'Digest',
                  'CreatedSince', 'CreatedAt', 'Size']
        args = ['images', '--format',
                SEPARATOR.join(['{{{{.{}}}}}'.format(x) for x in params])]
        for key, value in filters.items():
            args += ['-f', '{}={}'.format(key, value)]
        if name is not None:
            args.append(name)
        proc = DockerProcess(self, args, stdout=PIPE)
        for line in proc.stderr.read().splitlines():
            self.logger.error(line)
        proc.wait()
        params_map = dict([(x, re.sub(
            '((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))', r'_\1', x).lower()) for x in params])
        for line in proc.stdout.read().splitlines():
            image = {}
            values = line.split(SEPARATOR)
            for num, param in enumerate(params):
                if param == 'CreatedAt':
                    image[params_map[param]] = parse_datetime(values[num]).astimezone(
                        tzlocal.get_localzone()).replace(tzinfo=None)
                else:
                    image[params_map[param]] = values[num] \
                        if values[num] and values[num] != '<none>' else None
            if image['repository'] and image['tag']:
                image['image'] = "{}:{}".format(image['repository'], image['tag'])
            else:
                image['image'] = image['id']
            yield image

    def import_archives(self, image, *archives):
        paths = set()
        args = ['import', '-', image]
        proc = DockerProcess(self, args, stdin=PIPE)
        tar_out = tarfile.open(fileobj=proc.stdin, mode='w|')
        def layout_filter(obj, arc):
            if not obj.name.startswith(os.sep):
                obj.name = "/{}".format(obj.name)
            obj.name = os.path.normpath(obj.name)
            if arc.prefix:
                obj.name = os.path.join(
                    arc.prefix, obj.name.lstrip(os.sep))
            if obj.name.endswith('/') and len(obj.name) > 1:
                obj.name = obj.name[:-1]
            if obj.type == tarfile.LNKTYPE and obj.linkname:
                if obj.linkname.startswith(".{}".format(os.sep)):
                    obj.linkname = obj.linkname[1:]
                if obj.linkname.startswith(os.sep) and arc.prefix:
                    obj.linkname = os.path.join(
                        arc.prefix, obj.linkname.lstrip(os.sep))
                if obj.linkname.endswith('/') and len(obj.linkname) > 1:
                    obj.linkname = obj.linkname[:-1]
            return obj
        for archive in archives:
            self.logger.info("Importing archive \"%s\" into image \"%s:%s\"",
                             archive, image, archive.prefix or '/')

            tar_in = tarfile.open(name=archive.path, mode='r')
            if archive.prefix:
                segments = [os.sep]
                for segment in os.path.dirname(archive.prefix).split(os.sep):
                    segments.append(segment)
                    path = os.path.join(*segments)
                    if path in paths:
                        continue
                    tarinfo = tarfile.TarInfo(path)
                    tarinfo.mode = 0o755
                    tarinfo.uid = 0
                    tarinfo.gid = 0
                    tarinfo.type = tarfile.DIRTYPE
                    tar_out.addfile(tarinfo)
                    paths.add(tarinfo.name)
            for tarinfo in [layout_filter(obj, archive) for obj in tar_in]: # pylint: disable=cell-var-from-loop
                if tarinfo.name in paths:
                    continue
                paths.add(tarinfo.name)
                if tarinfo.isreg():
                    tar_out.addfile(
                        tarinfo, fileobj=tar_in.extractfile(tarinfo))
                else:
                    tar_out.addfile(tarinfo)
        tar_out.close()
        proc.stdin.close()
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error importing archives \"{}\" in image \"{}\"".format(archives, image), proc)

    def import_path(self, path, image):
        """
        Example:

            >>> import shutil
            >>> dm = DockerEngine(machine_name='default')
            >>> root = tempfile.mkdtemp()
            >>> image = "test_import_path:latest"
            >>> dm.import_path(root, image)
            >>> bool(dm.images(name=image))
            True
            >>> dm.remove_image(image)
            >>> shutil.rmtree(root)
        """
        self.logger.info(
            "Importing path \"%s\" into image \"%s\"", path, image)

        def layout_filter(obj):
            obj.uid = 0
            obj.gid = 0
            return obj
        args = ['import', '-', image]
        proc = DockerProcess(self, args, stdin=PIPE, stdout=FNULL)
        tar = tarfile.open(fileobj=proc.stdin, mode='w|')
        tar.add(path, arcname=".", filter=layout_filter)
        tar.close()
        proc.stdin.close()
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error importing archive \"{}\" in image \"{}\"".format(path, image), proc)

    def install_freeze(self, container, arch=None):
        self.logger.info("Installing freeze on container \"%s\"", container)

        def layout_filter(obj):
            obj.uid = 0
            obj.gid = 0
            return obj
        if arch is None:
            arch = self.platform
        args = ['cp', '-', "{}:/".format(container)]
        proc = DockerProcess(self, args, stdin=PIPE)
        tar = tarfile.open(fileobj=proc.stdin, mode='w|')
        bindir = tarfile.TarInfo(name="bin")
        bindir.uid = 0
        bindir.gid = 0
        bindir.mode = 0o0755
        bindir.type = tarfile.DIRTYPE
        tar.addfile(bindir)
        tar.add(os.path.join(os.path.dirname(__file__), 'freeze', 'freeze_{}'.format(
            arch)), arcname="bin/freeze", filter=layout_filter)
        tar.close()
        proc.stdin.close()
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error installing freeze on container \"{}\"".format(container), proc)

    def load_archive(self, container, name, fileobj, root="/", uid=None, gid=None):
        self.logger.info(
            "Loading archive \"%s\" on container \"%s\"", name, container)

        def layout_filter(obj):
            if uid is not None:
                obj.uid = uid
            if gid is not None:
                obj.gid = gid
            return obj
        args = ['cp', '-', "{}:{}".format(container, root)]
        proc = DockerProcess(self, args, stdin=PIPE)
        tar_in = tarfile.open(fileobj=fileobj, mode='r|*')
        tar_out = tarfile.open(fileobj=proc.stdin, mode='w|')
        for tarinfo in tar_in:
            tarinfo = layout_filter(tarinfo)
            if tarinfo.name in ['./lib', './usr/lib'] and tarinfo.isdir():
                lib64_tarinfo = deepcopy(tarinfo)
                lib64_tarinfo.name = "{}64".format(lib64_tarinfo.name)
                tar_out.addfile(lib64_tarinfo)
                tarinfo.type = tarfile.SYMTYPE
                tarinfo.linkname = os.path.basename(lib64_tarinfo.name)
            if tarinfo.isreg():
                tar_out.addfile(tarinfo, fileobj=tar_in.extractfile(tarinfo))
            else:
                tar_out.addfile(tarinfo)
        tar_out.close()
        proc.stdin.close()
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error loading archive on container \"{}\"".format(container), proc)

    def load_layout(self, container, path, root="/", uid=0, gid=0):
        self.logger.info(
            "Loading layout \"%s\" on container \"%s\"", path, container)

        def layout_filter(obj):
            obj.uid = uid
            obj.gid = gid
            return obj
        args = ['cp', '-', "{}:{}".format(container, root)]
        proc = DockerProcess(self, args, stdin=PIPE)
        tar = tarfile.open(fileobj=proc.stdin, mode='w|')
        tar.add(path, arcname=".", filter=layout_filter)
        tar.close()
        proc.stdin.close()
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error loading layout on container \"{}\"".format(container), proc)


    @listify
    def networks(self, **filters):
        params = ['id', 'name', 'driver']
        args = ['network', 'ls']
        for key, value in filters.items():
            args += ['--filter', '{}={}'.format(key, value)]
        proc = DockerProcess(self, args, stdout=PIPE)
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error requesting \"docker {}\"".format(' '.join(args)), proc)
        for line in proc.stdout.read().splitlines()[1:]:
            network = {}
            values = line.split()
            for num, param in enumerate(params):
                network[param] = values[num] if values[num] else None
            yield network

    def process_path(self, container, path, func):
        self.logger.info(
            "Processing path \"%s\" on container \"%s\"", path, container)
        args = ['cp', "{}:{}".format(container, path), "-"]
        proc = DockerProcess(self, args, stdout=PIPE)
        tar = tarfile.open(fileobj=proc.stdout, mode='r|')
        for tarinfo in tar:
            func(tar, tarinfo)
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error processing path on container \"{}\"".format(container), proc)

    def push_image(self, image, username, password, registry='index.docker.io'):
        self.logger.info(
            "Pushing image \"%s\" to registry \"%s\"", image, registry)
        full_image_name = '{}/{}'.format(registry, image)
        args = ['push', full_image_name]
        with DockerRegistryLogin(self, registry, username, password) as login:
            proc = DockerProcess(self, args, stdout=FNULL, config=login.config_path)
            if proc.wait() != 0:
                raise ExternalProcessError(
                    "Error pushing image \"{}\"".format(full_image_name), proc)

    def pull_image(self, image, username=None, password=None, registry='index.docker.io'):
        self.logger.info(
            "Pulling image \"%s\" from registry \"%s\"", image, registry)
        full_image_name = '{}/{}'.format(registry, image)
        args = ['pull', full_image_name]
        if username and password:
            with DockerRegistryLogin(self, registry, username, password) as login:
                proc = DockerProcess(self, args, stdout=FNULL, config=login.config_path)
                if proc.wait() != 0:
                    raise ExternalProcessError(
                        "Error pulling image \"{}\"".format(full_image_name), proc)
        else:
            proc = DockerProcess(self, args, stdout=FNULL)
            if proc.wait() != 0:
                raise ExternalProcessError(
                    "Error pulling image \"{}\"".format(full_image_name), proc)

    def remove_container(self, container):
        try:
            status = list(self.containers(include_stopped=True, name=container))[0]['status']
        except IndexError:
            status = None
        if status in ['running', 'paused']:
            self.logger.info("Stopping container \"%s\"", container)
            proc = DockerProcess(self, ['stop', container], stdout=FNULL)
            if proc.wait() != 0:
                raise ExternalProcessError(
                    "Error stopping container \"{}\"".format(container), proc)
        if status is not None:
            self.logger.info("Removing container \"%s\"", container)
            proc = DockerProcess(self, ['rm', container], stdout=FNULL)
            if proc.wait() != 0:
                raise ExternalProcessError(
                    "Error removing container \"{}\"".format(container), proc)

    def remove_image(self, name):
        for container in self.containers(include_stopped=True, ancestor=name):
            self.remove_container(container['names'][0])
        for image in self.images(name=name):
            self.logger.info("Removing image \"%s\"", image['image'])
            proc = DockerProcess(self, ['rmi', image['image']], stdout=FNULL)
            if proc.wait() != 0:
                raise ExternalProcessError(
                    "Error removing image \"{}\"".format(image['image']), proc)

    def remove_network(self, network):
        for container in self.containers(include_stopped=True, network=network):
            self.remove_container(container)
        self.logger.info("Removing network \"%s\"", network)
        proc = DockerProcess(self, ['network', 'rm', network], stdout=FNULL)
        if proc.wait() != 0:
            raise ExternalProcessError("Error removing network \"{}\"".format(network), proc)

    def remove_volume(self, volume):
        for container in self.containers(include_stopped=True, volume=volume):
            self.remove_container(container)
        self.logger.info("Removing volume \"%s\"", volume)
        proc = DockerProcess(self, ['volume', 'rm', volume], stdout=FNULL)
        if proc.wait() != 0:
            raise ExternalProcessError("Error removing volume \"{}\"".format(volume), proc)

    def run_cmd(self, container, cmd, privileged=False,
                quiet=False, return_output=False, user=None):
        if not quiet:
            self.logger.info(
                "Running command \"%s\" on \"%s\"", cmd, container)
        args = ['exec']
        if privileged:
            args.append('--privileged')
        if user:
            args += ['-u', user]
        args += [container] + self.shell.split(' ') + ['-c', cmd]
        proc = DockerProcess(self, args, stdout=PIPE if return_output else None)
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error running command \"{}\" on container \"{}\"".format(cmd, container), proc)
        if return_output:
            return proc.stdout.read().strip()

    def run_script(self, container, script, privileged=False, shell=None, user=None):
        self.logger.info("Running script on \"%s\"", container)
        args = ['exec', '-i']
        if privileged:
            args.append('--privileged')
        if user:
            args += ['-u', user]
        if shell is None:
            shell = self.shell
        args += [container] + shell.split(' ')
        proc = DockerProcess(self, args, stdin=PIPE)
        proc.stdin.write(script)
        proc.stdin.close()
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error running script on container \"{}\"".format(container), proc)

    def save_layout(self, container, src, dst):
        self.logger.info(
            "Saving layout \"%s:%s\" on path \"%s\"", container, src, dst)
        args = ['cp', "{}:{}".format(container, src), "-"]
        proc = DockerProcess(self, args, stdout=PIPE)
        tar = tarfile.open(fileobj=proc.stdout, mode='r|')
        for member in tar:
            member.name = os.path.normpath(member.name.lstrip('/'))
            tar.extract(member, dst)
        tar.close()
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error saving layout from container \"{}\"".format(container), proc)

    def start_container(self, container):
        self.logger.info("Starting container \"%s\"", container)
        proc = DockerProcess(self, ['start', container], stdout=FNULL)
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error creating container \"{}\"".format(container), proc)

    @listify
    def volumes(self, **filters):
        params = ['driver', 'name']
        args = ['volume', 'ls']
        for key, value in filters.items():
            args += ['-f', '{}={}'.format(key, value)]
        proc = DockerProcess(self, args, stdout=PIPE)
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error requesting \"docker {}\"".format(' '.join(args)), proc)
        for line in proc.stdout.read().splitlines()[1:]:
            volume = {}
            values = line.split()
            for num, param in enumerate(params):
                volume[param] = values[num] if values[num] else None
            yield volume

class BaseDockerSubRecipe(BaseSubRecipe):

    def initialize(self):
        super(BaseDockerSubRecipe, self).initialize()
        self.engine = DockerEngine(
            logger=self.logger,
            machine_name=self.options.get('machine-name', None),
            url=self.options.get('engine-url', None),
            tlsverify=self.options.get('engine-tls-verify', None),
            tlscertpath=self.options.get('engine-tls-cert-path', None),
            shell=self.shell,
            timeout=int(self.options.get(
                'timeout', DEFAULT_TIMEOUT)))

    def is_image_updated(self, name):
        if not os.path.exists(self.completed):
            return True
        completed_mtime = datetime.fromtimestamp(
            os.stat(self.completed).st_mtime)
        for image in self.engine.images(name=name):
            if image['created_at'] > completed_mtime:
                return True
        return False

    def is_layout_updated(self, layout):
        if not os.path.exists(self.completed):
            return True
        completed_mtime = os.stat(self.completed).st_mtime
        for dirname, _, files in os.walk(layout):
            if os.stat(dirname).st_mtime > completed_mtime:
                return True
            for filename in files:
                if os.lstat(os.path.join(dirname, filename)).st_mtime > completed_mtime:
                    return True
        return False
