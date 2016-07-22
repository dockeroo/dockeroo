
from __future__ import absolute_import

import base64
from copy import deepcopy
from collections import namedtuple
from datetime import datetime
from distutils.dir_util import copy_tree
import json
import logging
import os
import platform
import re
from shellescape import quote
from shutil import rmtree
from StringIO import StringIO
from subprocess import Popen, PIPE, STDOUT
import tarfile
import tempfile
import time
import tzlocal
from zc.buildout import UserError
from zc.buildout.download import Download

from dockeroo.utils import mkdir, reify, parse_datetime


logging.getLogger(
    "requests.packages.urllib3.connectionpool").setLevel(logging.WARN)

DEFAULT_TIMEOUT = 180

FNULL = open(os.devnull, 'w')


class DockerError(RuntimeError):

    def __init__(self, msg, process):
        full_msg = "{} ({})".format(msg, process.returncode)
        err = ' '.join(process.stderr.read().split(os.linesep))
        if err:
            full_msg = "{}: {}".format(full_msg, err)
        return super(DockerError, self).__init__(full_msg)


class Archive(object):

    def __init__(self, url=None, path=None, prefix=None, md5sum=None):
        self.url = url
        self.path = path
        self.prefix = prefix
        self.md5sum = md5sum

    def download(self, buildout):
        download = Download(buildout['buildout'], hash_name=False)
        self.path, is_temp = download(self.url, md5sum=self.md5sum)

    def __repr__(self):
        return self.url or self.path


class DockerProcess(Popen):

    def __init__(self, machine, args, stdin=None, stdout=None, stderr=PIPE, env={}, config=None):
        self.machine = machine
        args = ['docker'] + args
        if config is not None:
            args = ['--config', config] + args
        custom_env = os.environ.copy()
        custom_env.update(machine.client_environment)
        custom_env.update(env)
        return super(DockerProcess, self).__init__(
            args, stdin=stdin, stdout=stdout, stderr=stderr, close_fds=True, env=custom_env)


class DockerMachineProcess(Popen):

    def __init__(self, args, stdin=None, stdout=None):
        args = ['docker-machine'] + args
        return super(DockerMachineProcess, self).__init__(
            args, stdin=stdin, stdout=stdout, stderr=PIPE, close_fds=True)


class DockerRegistryLogin(object):

    def __init__(self, machine, registry, username, password):
        self.machine = machine
        self.registry = "https://{}/v1/".format(registry)
        self.username = username
        self.password = password

    def __enter__(self):
        self.config_path = tempfile.mkdtemp()
        p = DockerProcess(self.machine,
                          ['login', '-u', self.username, '-p', self.password, self.registry],
                          config=self.config_path)
        if p.wait() != 0:
            raise DockerError("Error requesting \"docker login {}\"".format(self.registry), p)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        rmtree(self.config_path)


class DockerMachine(object):

    def __init__(self, machine_name='default', logger=None, shell='/bin/sh', timeout=DEFAULT_TIMEOUT):
        self.machine_name = machine_name
        self.logger = logging.getLogger(logger or self.machine_name)
        self.shell = shell
        self.timeout = timeout

    @reify
    def client_environment(self):
        p = DockerMachineProcess(['inspect', self.machine_name], stdout=PIPE)
        if p.wait() != 0:
            raise DockerError("Error requesting \"docker-machine inspect {}\"".format(self.machine_name), p)
        inspect = json.loads(p.stdout.read())

        return {
            'DOCKER_TLS_VERIFY': str(int(inspect['HostOptions']['EngineOptions']['TlsVerify'])),
            'DOCKER_HOST': self.machine_url,
            'DOCKER_CERT_PATH': inspect['HostOptions']['AuthOptions']['StorePath'].encode('utf-8'),
            'DOCKER_MACHINE_NAME': self.machine_name,
        }

    @reify
    def client_version(self):
        p = DockerProcess(self, ['version', '-f', '{{.Client.Version}}'], stdout=PIPE)
        if p.wait() != 0:
            raise DockerError("Error requesting version", p)
        return p.stdout.read().rstrip(os.linesep)

    @reify
    def machine_platform(self):
        return self.machine_run_cmd("uname -m", quiet=True, return_output=True)

    @reify
    def machine_url(self):
        p = DockerMachineProcess(['url', self.machine_name], stdout=PIPE)
        if p.wait() != 0:
            raise DockerError("Error requesting \"docker-machine url {}\"".format(self.machine_name), p)
        return p.stdout.read().rstrip(os.linesep)

    def build_dockerfile(self, tag, path, **kwargs):
        self.logger.info("Building Dockerfile from context \"%s\"", path)
        args = ['build', '-t', tag]
        for k, v in kwargs.items():
            args += ['--build-arg', '{}={}'.format(k, v)]
        args.append(path)
        p = DockerProcess(self, args)
        if p.wait() != 0:
            raise DockerError("Error building Dockerfile from context \"{}\"".format(path), p)

    def clean_stale_images(self):
        for image in self.images(dangling='true'):
            self.remove_image(image['image'])
        for image in self.images('<none>'):
            self.remove_image(image['image'])

    def commit_container(self, container, image, command=None, user=None, labels={}, expose=[], volumes=[]):
        self.logger.info(
            "Committing container \"%s\" to image \"%s\"", container, image)
        args = ['commit']
        if command:
            args.append(
                "--change='CMD [{}]'".format(', '.join(map(lambda x: '"{}"'.format(x), command.split()))))
        if user:
            args.append("--change='USER \"{}\"'".format(user))
        for k, v in labels.items():
            args.append("--change='LABEL \"{}\"=\"{}\"".format(k, v))
        for port in expose:
            args.append("--change='EXPOSE {}'".format(port))
        if volumes:
            args.append(
                "--change='VOLUME [{}]'".format(', '.join(map(lambda x: '"{}"'.format(x), volumes))))
        args += [container, image]
        p = DockerProcess(self, args, stdout=FNULL)
        if p.wait() != 0:
            raise DockerError(
                "Error committing container \"{}\"".format(container), p)

    def config_binfmt(self, container, platform):
        self.run_cmd(
            container, '[ -f /proc/sys/fs/binfmt_misc/register ] || mount binfmt_misc -t binfmt_misc /proc/sys/fs/binfmt_misc', privileged=True)
        self.run_cmd(container, '[ -f /proc/sys/fs/binfmt_misc/{platform} ] || echo "{binfmt}" >/proc/sys/fs/binfmt_misc/register'.format(platform=platform, binfmt={
            'aarch64': r':{platform}:M::\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\xb7:\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff:/usr/bin/qemu-{platform}:',
            'arm':     r':{platform}:M::\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x28\x00:\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff:/usr/bin/qemu-{platform}:',
            'armeb':   r':{platform}:M::\x7fELF\x01\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x28:\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff:/usr/bin/qemu-{platform}:',
            'alpha':   r':{platform}:M::\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x26\x90:\xff\xff\xff\xff\xff\xfe\xfe\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff:/usr/bin/qemu-{platform}:',
            'mips':    r':{platform}:M::\x7fELF\x01\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x08:\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff:/usr/bin/qemu-{platform}:',
            'mipsel':  r':{platform}:M::\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x08\x00:\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff:/usr/bin/qemu-{platform}:',
            'ppc':     r':{platform}:M::\x7fELF\x01\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x14:\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff:/usr/bin/qemu-{platform}:',
            'sh4':     r':{platform}:M::\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x2a\x00:\xff\xff\xff\xff\xff\xff\xff\x00\xff\xff\xff\xff\xff\xff\xff\xff\xfb\xff\xff\xff:/usr/bin/qemu-{platform}:',
            'sh4eb':   r':{platform}:M::\x7fELF\x01\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x2a:\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff:/usr/bin/qemu-{platform}:',
            'sparc':   r':{platform}:M::\x7fELF\x01\x02\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x02:\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff:/usr/bin/qemu-{platform}:',
        }[platform].format(platform=platform)), privileged=True)

    def containers(self, all=False, **filters):
        SEP = '|'
        params = ['ID', 'Image', 'Command', 'CreatedAt', 'RunningFor',
                  'Ports', 'Status', 'Size', 'Names', 'Labels', 'Mounts']
        args = ['ps', '--format',
                SEP.join(map(lambda x: '{{{{.{}}}}}'.format(x), params))]
        if all:
            args.append('-a')
        for k, v in filters.items():
            args += ['-f', '{}={}'.format(k, v)]
        p = DockerProcess(self, args, stdout=PIPE)
        for line in p.stderr.read().split(os.linesep)[:-1]:
            self.logger.error(line)
        p.wait()
        params_map = dict(map(lambda x: (x, re.sub(
            '((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))', r'_\1', x).lower()), params))
        ret = []
        for line in p.stdout.read().split(os.linesep)[:-1]:
            d = {}
            values = line.split(SEP)
            for n, param in enumerate(params):
                if param in ['Labels', 'Mounts', 'Names', 'Ports']:
                    d[params_map[param]] = values[n].split(',') if values[
                        n] else []
                    if param == 'Labels':
                        d[params_map[param]] = map(lambda x: tuple(
                            x.split('=')), d[params_map[param]])
                    elif param == 'Ports':
                        d[params_map[param]] = map(lambda x: tuple(
                            x.split('->')), d[params_map[param]])
                elif param == 'Status':
                    d[params_map[param]] = {
                        'created': 'created',
                        'dead': 'dead',
                        'exited': 'exited',
                        'paused': 'paused',
                        'restarting': 'restarting',
                        'up': 'running',
                    }[values[n].split(' ')[0].lower()]
                elif param == 'CreatedAt':
                    d[params_map[param]] = parse_datetime(values[n]).astimezone(
                        tzlocal.get_localzone()).replace(tzinfo=None)
                else:
                    d[params_map[param]] = values[n] if values[n] else None
            ret.append(d)
        return ret

    def copy_image_to_container(self, image, container, src, dst):
        tmp = self.get_random_name()
        self.create_container(tmp, image)
        self.copy_path(tmp, container, src, dst=dst, dst_exec=True)
        self.remove_container(tmp)

    def copy_layout(self, src, dst):
        self.logger.info("Copying layout \"%s\" on \"%s\"", src, dst)
        return copy_tree(src, dst)

    def copy_path(self, container_src, container_dst, src, dst=None, dst_exec=False):
        if dst is None:
            dst = os.path.join(*os.path.dirname(src).split(os.sep))
        self.logger.info("Copying files from container \"%s:%s\" to container \"%s:/%s\"",
                         container_src, src, container_dst, dst)
        if src.endswith('/'):
            src_prefix = os.path.dirname(src).split(os.sep)[-1] + '/'
        else:
            src_prefix = ''

        def layout_filter(f):
            if dst is not None:
                if len(f.name) > len(src_prefix):
                    f.name = os.path.join(dst, f.name[len(src_prefix):])
                else:
                    f.name = dst
                if f.type == tarfile.LNKTYPE:
                    if len(f.linkname) > len(src_prefix):
                        f.linkname = os.path.join(
                            dst, f.linkname[len(src_prefix):])
                    else:
                        f.linkname = dst
            return f
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
            tarinfo = layout_filter(tarinfo)
            if tarinfo.isreg():
                tar_out.addfile(tarinfo, fileobj=tar_in.extractfile(tarinfo))
            else:
                tar_out.addfile(tarinfo)
        tar_in.close()
        tar_out.close()
        p_in.stdout.close()
        p_out.stdin.close()
        if p_in.wait() != 0:
            raise DockerError("Error processing path on container \"{}\"".format(container_src), p_in)
        if p_out.wait() != 0:
            raise DockerError(
                "Error processing path on container \"{}\"".format(container_dst), p_out)

    def create_container(self, container, image, command=None, privileged=False, run=False, tty=False,
                         volumes=None, volumes_from=None, user=None, networks=[], links={},
                         network_aliases=[], env={}, ports={}):
        if not any(filter(lambda x: container in x['names'], self.containers(all=True))):
            self.logger.info("Creating container \"%s\"", container)
            args = ['create', '--name="{}"'.format(container)]
            for k, v in env.items():
                args += ['-e', "{}={}".format(k, v)]
            for k, v in ports.items():
                args += ['-p', "{}:{}".format(k, v)]
            for k, v in links.items():
                args += ['--link', "{}:{}".format(k, v)]
            for network in networks:
                args += ['--network', network]
            for network_alias in network_aliases:
                args += ['--network-alias', network_alias]
            if privileged:
                args.append('--privileged')
            if tty:
                args.append('--tty')
            if user:
                args += ['-u', user]
            if volumes:
                args += map(lambda (name, path): "--volume={}:{}".format(name, path), volumes)
            if volumes_from:
                args.append("--volumes-from={}".format(volumes_from))
            args.append(image)
            if command:
                args += command.split(" ")
            p = DockerProcess(self, args, stdout=FNULL)
            if p.wait() != 0:
                raise DockerError(
                    "Error creating container \"{}\"".format(container), p)
        if run:
            self.start_container(container)

    def create_network(self, network, driver='bridge', gateway=None, subnet=None, ip_range=None, ipv6=False, internal=False):
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
        p = DockerProcess(self, args)
        if p.wait() != 0:
            raise DockerError("Error creating network \"{}\"".format(network), p)

    def create_volume(self, volume):
        if any(filter(lambda x: volume == x['name'], self.volumes())):
            return
        self.logger.info("Creating volume \"%s\"", volume)
        args = ['volume', 'create', '--name="{}"'.format(volume)]
        p = DockerProcess(self, args, stdout=FNULL)
        if p.wait() != 0:
            raise DockerError("Error creating volume \"{}\"".format(volume), p)

    def export_files(self, container, src, dst):
        self.logger.info(
            "Export files from \"%s:%s\" to path \"%s\"", container, src, dst)
        args = ['cp', "{}:{}".format(container, src), "-"]
        p = DockerProcess(self, args, stdout=PIPE)
        tar = tarfile.open(fileobj=p.stdout, mode='r|')
        for fin in tar:
            if not fin.isreg():
                continue
            fout = open(os.path.join(dst, os.path.basename(fin.name)), 'w')
            fout.write(tar.extractfile(fin).read())
            fout.close()
        tar.close()
        if p.wait() != 0:
            raise DockerError(
                "Error exporting files from container \"{}\"".format(container), p)

    def get_random_name(self):
        return next(tempfile._get_candidate_names())

    def get_container_ip_address(self, container):
        args = ['inspect', '--format="{{.NetworkSettings.IPAddress}}"', container]
        p = DockerProcess(self, args, stdout=PIPE)
        if p.wait() != 0:
            raise DockerError(
                "Error running command \"{}\" on machine \"{}\"".format(cmd, self.machine_name), p)
        return p.stdout.read().rstrip(os.linesep)

    def machine_run_cmd(self, cmd, quiet=False, return_output=False):
        if not quiet:
            self.logger.info("Running command \"%s\" on machine \"%s\"", cmd, self.machine_name)
        args = ['ssh', self.machine_name, cmd]
        p = DockerMachineProcess(args, stdout=PIPE if return_output else None)
        if p.wait() != 0:
            raise DockerError(
                "Error running command \"{}\" on machine \"{}\"".format(cmd, self.machine_name), p)
        if return_output:
            return p.stdout.read().strip()

    def images(self, name=None, **filters):
        SEP = '|'
        params = ['ID', 'Repository', 'Tag', 'Digest',
                  'CreatedSince', 'CreatedAt', 'Size']
        args = ['images', '--format',
                SEP.join(map(lambda x: '{{{{.{}}}}}'.format(x), params))]
        for k, v in filters.items():
            args += ['-f', '{}={}'.format(k, v)]
        if name is not None:
            args.append(name)
        p = DockerProcess(self, args, stdout=PIPE)
        for line in p.stderr.read().split(os.linesep)[:-1]:
            self.logger.error(line)
        p.wait()
        params_map = dict(map(lambda x: (x, re.sub(
            '((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))', r'_\1', x).lower()), params))
        ret = []
        for line in p.stdout.read().split(os.linesep)[:-1]:
            d = {}
            values = line.split(SEP)
            for n, param in enumerate(params):
                if param == 'CreatedAt':
                    d[params_map[param]] = parse_datetime(values[n]).astimezone(
                        tzlocal.get_localzone()).replace(tzinfo=None)
                else:
                    d[params_map[param]] = values[n] if values[
                        n] and values[n] != '<none>' else None
            if d['repository'] and d['tag']:
                d['image'] = "{}:{}".format(d['repository'], d['tag'])
            else:
                d['image'] = d['id']
            ret.append(d)
        return ret

    def import_archives(self, image, *archives):
        paths = set()
        args = ['import', '-', image]
        p = DockerProcess(self, args, stdin=PIPE)
        tar_out = tarfile.open(fileobj=p.stdin, mode='w|')
        for archive in archives:
            self.logger.info("Importing archive \"%s\" into image \"%s:%s\"",
                             archive, image, archive.prefix or '/')

            def layout_filter(f):
                if not f.name.startswith(os.sep):
                    f.name = "/{}".format(f.name)
                f.name = os.path.normpath(f.name)
                if archive.prefix:
                    f.name = os.path.join(
                        archive.prefix, f.name.lstrip(os.sep))
                if f.name.endswith('/') and len(f.name) > 1:
                    f.name = f.name[:-1]
                if f.type == tarfile.LNKTYPE and f.linkname:
                    if f.linkname.startswith(".{}".format(os.sep)):
                        f.linkname = f.linkname[1:]
                    if f.linkname.startswith(os.sep) and archive.prefix:
                        f.linkname = os.path.join(
                            archive.prefix, f.linkname.lstrip(os.sep))
                    if f.linkname.endswith('/') and len(f.linkname) > 1:
                        f.linkname = f.linkname[:-1]
                return f
            tar_in = tarfile.open(name=archive.path, mode='r')
            if archive.prefix:
                d = [os.sep]
                for s in os.path.dirname(archive.prefix).split(os.sep):
                    d.append(s)
                    path = os.path.join(*d)
                    if path in paths:
                        continue
                    tarinfo = tarfile.TarInfo(path)
                    tarinfo.mode = 0755
                    tarinfo.uid = 0
                    tarinfo.gid = 0
                    tarinfo.type = tarfile.DIRTYPE
                    tar_out.addfile(tarinfo)
                    paths.add(tarinfo.name)
            for tarinfo in map(layout_filter, tar_in):
                if tarinfo.name in paths:
                    continue
                paths.add(tarinfo.name)
                if tarinfo.isreg():
                    tar_out.addfile(
                        tarinfo, fileobj=tar_in.extractfile(tarinfo))
                else:
                    tar_out.addfile(tarinfo)
        tar_out.close()
        p.stdin.close()
        if p.wait() != 0:
            raise DockerError(
                "Error importing archives \"{}\" in image \"{}\"".format(archives, image), p)

    def import_path(self, path, image):
        self.logger.info(
            "Importing path \"%s\" into image \"%s\"", path, image)

        def layout_filter(f):
            f.uid = 0
            f.gid = 0
            return f
        args = ['import', '-', image]
        p = DockerProcess(self, args, stdin=PIPE, stdout=FNULL)
        tar = tarfile.open(fileobj=p.stdin, mode='w|')
        tar.add(path, arcname=".", filter=layout_filter)
        tar.close()
        p.stdin.close()
        if p.wait() != 0:
            raise DockerError(
                "Error importing archive \"{}\" in image \"{}\"".format(path, image), p)

    def install_freeze(self, container, platform=None):
        self.logger.info("Installing freeze on container \"%s\"", container)

        def layout_filter(f):
            f.uid = 0
            f.gid = 0
            return f
        if platform is None:
            platform = self.machine_platform
        args = ['cp', '-', "{}:/".format(container)]
        p = DockerProcess(self, args, stdin=PIPE)
        tar = tarfile.open(fileobj=p.stdin, mode='w|')
        tar.add(os.path.join(self.buildout['buildout'][
                'bin-directory']), arcname="bin", filter=layout_filter, recursive=False)
        tar.add(os.path.join(os.path.dirname(__file__), 'freeze', 'freeze_{}'.format(
            platform)), arcname="bin/freeze", filter=layout_filter)
        tar.close()
        p.stdin.close()
        if p.wait() != 0:
            raise DockerError(
                "Error installing freeze on container \"{}\"".format(container), p)

    def load_archive(self, container, name, fileobj, root="/"):
        self.logger.info(
            "Loading archive \"%s\" on container \"%s\"", name, container)

        def layout_filter(f):
            f.uid = 0
            f.gid = 0
            return f
        args = ['cp', '-', "{}:{}".format(container, root)]
        p = DockerProcess(self, args, stdin=PIPE)
        tar_in = tarfile.open(fileobj=fileobj, mode='r|*')
        tar_out = tarfile.open(fileobj=p.stdin, mode='w|')
        for tarinfo in tar_in:
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
        p.stdin.close()
        if p.wait() != 0:
            raise DockerError(
                "Error loading archive on container \"{}\"".format(container), p)

    def load_layout(self, container, path, root="/", uid=0, gid=0):
        self.logger.info(
            "Loading layout \"%s\" on container \"%s\"", path, container)

        def layout_filter(f):
            f.uid = uid
            f.gid = gid
            return f
        args = ['cp', '-', "{}:{}".format(container, root)]
        p = DockerProcess(self, args, stdin=PIPE)
        tar = tarfile.open(fileobj=p.stdin, mode='w|')
        tar.add(path, arcname=".", filter=layout_filter)
        tar.close()
        p.stdin.close()
        if p.wait() != 0:
            raise DockerError(
                "Error loading layout on container \"{}\"".format(container), p)

    def networks(self, **filters):
        params = ['id', 'name', 'driver']
        args = ['network', 'ls']
        for k, v in filters.items():
            args += ['--filter', '{}={}'.format(k, v)]
        p = DockerProcess(self, args, stdout=PIPE)
        if p.wait() != 0:
            raise DockerError("Error requesting \"docker {}\"".filter(' '.join(args)), p)
        ret = []
        for line in p.stdout.read().split(os.linesep)[1:-1]:
            d = {}
            values = line.split()
            for n, param in enumerate(params):
                d[param] = values[n] if values[n] else None
            ret.append(d)
        return ret

    def process_path(self, container, path, fn):
        self.logger.info(
            "Processing path \"%s\" on container \"%s\"", path, container)
        args = ['cp', "{}:{}".format(container, path), "-"]
        p = DockerProcess(self, args, stdout=PIPE)
        tar = tarfile.open(fileobj=p.stdout, mode='r|')
        for tarinfo in tar:
            fn(tar, tarinfo)
        if p.wait() != 0:
            raise DockerError(
                "Error processing path on container \"{}\"".format(container), p)

    def push_image(self, image, username, password, registry='index.docker.io'):
        self.logger.info(
            "Pushing image \"%s\" to registry \"%s\"", image, registry)
        full_image_name = '{}/{}'.format(registry, image)
        args = ['push', full_image_name]
        with DockerRegistryLogin(self, registry, username, password) as login:
            p = DockerProcess(self, args, stdout=FNULL)
            if p.wait() != 0:
                raise DockerError(
                    "Error pushing image \"{}\"".format(full_image_name), p)

    def pull_image(self, image, username=None, password=None, registry='index.docker.io'):
        self.logger.info(
            "Pulling image \"%s\" from registry \"%s\"", image, registry)
        full_image_name = '{}/{}'.format(registry, image)
        args = ['pull', full_image_name]
        if username and password:
            with DockerRegistryLogin(registry, username, password) as login:
                p = DockerProcess(self, args, stdout=FNULL, config=login.config_path)
                if p.wait() != 0:
                    raise DockerError(
                        "Error pulling image \"{}\"".format(full_image_name), p)
        else:
            p = DockerProcess(self, args, stdout=FNULL)
            if p.wait() != 0:
                raise DockerError(
                    "Error pulling image \"{}\"".format(full_image_name), p)

    def remove_container(self, container):
        try:
            status = self.containers(all=True, name=container)[0]['status']
        except IndexError:
            status = None
        if status in ['running', 'paused']:
            self.logger.info("Stopping container \"%s\"", container)
            p = DockerProcess(self, ['stop', container], stdout=FNULL)
            if p.wait() != 0:
                raise DockerError(
                    "Error stopping container \"{}\"".format(container), p)
        if status is not None:
            self.logger.info("Removing container \"%s\"", container)
            p = DockerProcess(self, ['rm', container], stdout=FNULL)
            if p.wait() != 0:
                raise DockerError(
                    "Error removing container \"{}\"".format(container), p)

    def remove_image(self, name):
        for container in self.containers(all=True, ancestor=name):
            self.remove_container(container['names'][0])
        for image in self.images(name=name):
            p = DockerProcess(self, ['rmi', image['image']], stdout=FNULL)
            if p.wait() != 0:
                raise DockerError(
                    "Error removing image \"{}\"".format(image['image']), p)

    def remove_network(self, network):
        for container in self.containers(all=True, network=network):
            self.remove_container(container)
        self.logger.info("Removing network \"%s\"", network)
        p = DockerProcess(self, ['network', 'rm', network], stdout=FNULL)
        if p.wait() != 0:
            raise DockerError("Error removing network \"{}\"".format(network), p)

    def remove_volume(self, volume):
        for container in self.containers(all=True, volume=volume):
            self.remove_container(container)
        self.logger.info("Removing volume \"%s\"", volume)
        p = DockerProcess(self, ['volume', 'rm', volume], stdout=FNULL)
        if p.wait() != 0:
            raise DockerError("Error removing volume \"{}\"".format(volume), p)

    def run_cmd(self, container, cmd, privileged=False, quiet=False, return_output=False, user=None):
        if not quiet:
            self.logger.info(
                "Running command \"%s\" on \"%s\"", cmd, container)
        args = ['exec']
        if privileged:
            args.append('--privileged')
        if user:
            args += ['-u', user]
        args += [container] + self.shell.split(' ') + ['-c', cmd]
        p = DockerProcess(self, args, stdout=PIPE if return_output else None)
        if p.wait() != 0:
            raise DockerError(
                "Error running command \"{}\" on container \"{}\"".format(cmd, container), p)
        if return_output:
            return p.stdout.read().strip()

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
        p = DockerProcess(self, args, stdin=PIPE, stderr=None)
        p.stdin.write(script)
        p.stdin.close()
        if p.wait() != 0:
            raise DockerError(
                "Error running script on container \"{}\"".format(container), p)

    def save_layout(self, container, src, dst):
        self.logger.info(
            "Saving layout \"%s:%s\" on path \"%s\"", container, src, dst)
        args = ['cp', "{}:{}".format(container, src), "-"]
        p = DockerProcess(self, args, stdout=PIPE)
        tar = tarfile.open(fileobj=p.stdout, mode='r|')
        tar.extractall(dst)
        tar.close()
        if p.wait() != 0:
            raise DockerError(
                "Error saving layout from container \"{}\"".format(container), p)

    def start_container(self, container):
        self.logger.info("Starting container \"%s\"", container)
        p = DockerProcess(self, ['start', container], stdout=FNULL)
        if p.wait() != 0:
            raise DockerError(
                "Error creating container \"{}\"".format(container), p)

    def volumes(self, dangling=None):
        params = ['driver', 'name']
        args = ['volume', 'ls']
        if dangling is not None:
            args += ['-f', 'dangling={}'.format(str(dangling).lower())]
        p = DockerProcess(self, args, stdout=PIPE)
        if p.wait() != 0:
            raise DockerError("Error requesting \"docker {}\"".filter(' '.join(args)), p)
        ret = []
        for line in p.stdout.read().split(os.linesep)[1:-1]:
            d = {}
            values = line.split()
            for n, param in enumerate(params):
                d[param] = values[n] if values[n] else None
            ret.append(d)
        return ret


class DockerMachineRecipe(DockerMachine):

    def __init__(self, buildout, name, options):
        self.buildout, self.name, self.options = buildout, name, options
        return super(DockerMachineRecipe, self).__init__(
            logger=self.name,
            machine_name=self.options.get('machine', 'default'),
            shell=self.options.get(
                'shell', '/bin/sh'),
            timeout=int(self.options.get(
                'timeout', DEFAULT_TIMEOUT)))

    @reify
    def completed(self):
        return os.path.join(self.buildout['buildout']['parts-directory'], self.name, '.completed')

    @classmethod
    def _uninstall(cls, name, options):
        return cls({}, name, options).uninstall()

    def is_image_updated(self, name):
        if not os.path.exists(self.completed):
            return True
        completed_mtime = datetime.fromtimestamp(
            os.stat(self.completed).st_mtime)
        for image in self.images(name=name):
            if image['created_at'] > completed_mtime:
                return True
        return False

    def is_layout_updated(self, layout):
        if not os.path.exists(self.completed):
            return True
        completed_mtime = os.stat(self.completed).st_mtime
        for dirname, subdirs, files in os.walk(layout):
            if os.stat(dirname).st_mtime > completed_mtime:
                return True
            for filename in files:
                if os.lstat(os.path.join(dirname, filename)).st_mtime > completed_mtime:
                    return True
        return False

    def mark_completed(self, files=[]):
        location = os.path.join(self.buildout['buildout'][
                                'parts-directory'], self.name)
        mkdir(location)
        with open(self.completed, 'a'):
            os.utime(self.completed, None)
        return files + [self.completed]
