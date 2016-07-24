
import os
from shellescape import quote
import shutil
import tarfile
import tempfile

from dockeroo import DockerMachineRecipe
from dockeroo.utils import merge


class Recipe(DockerMachineRecipe):

    def __init__(self, buildout, name, options):
        super(Recipe, self).__init__(buildout, name, options)

        self.archives = []
        for url, prefix, md5sum in [merge([None, None, None], x.split())[:3] for x in [f for f in [x.strip() for x in self.options.get('archives', self.options.get('archive', '')).split('\n')] if f]]:
            if prefix == '/':
                prefix = None
            self.archives.append(
                Archive(url=url, prefix=prefix, md5sum=md5sum))

        self.accept_keywords = [f for f in [x.strip() for x in self.options.get('accept-keywords', '').split('\n')] if f]
        self.build_dependencies = [f for f in [x.strip() for x in self.options.get('build-dependencies', '').split('\n')] if f]
        self.build_command = self.options.get('build-command', "/bin/freeze")
        self.build_container = "{}_build".format(self.name)
        self.build_layout = self.options.get('build-layout', None)
        self.build_image = self.options.get('build-image', None)
        self.build_env = dict([y for y in [x.strip().split(
            '=') for x in self.options.get('build-env', '').split('\n')] if y[0]])
        self.build_volumes_from = self.options.get('build-volumes-from', None)
        self.build_script_user = self.options.get('build-script-user', None)
        self.build_script_shell = self.options.get(
            'build-script-shell', self.shell)
        self.build_script = "#!{}\n{}".format(self.build_script_shell,
                                              '\n'.join([f for f in [x.strip() for x in self.options.get('build-script').replace('$$', '$').split('\n')] if f])) if self.options.get('build-script', None) is not None else None

        self.assemble_container = "{}_assemble".format(self.name)
        self.copy = [merge([None, None], y.split()[:2]) for y in [f for f in [x.strip() for x in self.options.get('copy', '').split('\n')] if f]]
        self.base_image = self.options.get('base-image', None)
        self.keep = self.options.get('keep', 'false').strip(
        ).lower() in ('true', 'yes', 'on', '1')
        self.layout = self.options.get('layout', None)
        self.layout_uid = self.options.get('layout-uid', 0)
        self.layout_gid = self.options.get('layout-gid', 0)
        self.packages = [f for f in [x.strip() for x in self.options.get('packages', '').split('\n')] if f]
        self.platform = self.options.get('platform', self.machine_platform)
        self.arch = self.options.get('arch', self.platform)
        self.processor = self.options.get('processor', self.platform)
        self.variant = self.options.get('variant', 'dockeroo')
        self.abi = self.options.get('abi', 'gnu')
        self.script_user = self.options.get('script-user', None)
        self.script_shell = self.options.get('script-shell', self.shell)
        self.script = "#!{}\n{}".format(self.script_shell,
                                        '\n'.join([_f for _f in [x.strip() for x in self.options.get('script').replace('$$', '$').split('\n')] if _f])) if self.options.get('script', None) is not None else None
        self.tty = self.options.get('tty', 'false').strip(
        ).lower() in ('true', 'yes', 'on', '1')
        self.masks = [_f for _f in [x.strip() for x in self.options.get('mask', '').split('\n')] if _f]
        self.unmasks = [_f for _f in [x.strip() for x in self.options.get('unmask', '').split('\n')] if _f]
        self.uses = [_f for _f in [x.strip() for x in self.options.get('use', '').split('\n')] if _f]

        self.command = self.options.get('command', "/bin/freeze")
        self.user = self.options.get('user', None)
        self.labels = dict([y for y in [x.strip().split('=') for x in self.options.get('labels', '').split('\n')] if y[0]])
        self.expose = [_f for _f in [x.strip() for x in self.options.get('expose', '').split('\n')] if _f]
        self.volumes = [y for y in [x.strip().split(
            ':', 1) for x in self.options.get('volumes', '').split('\n')] if y[0]]
        self.volumes_from = self.options.get('volumes-from', None)

    def install(self):
        if self.base_image:
            base_image = self.base_image
        else:
            base_image = self.name
            if self.archives:
                for archive in self.archives:
                    archive.download(self.buildout)
                self.import_archives(base_image, *self.archives)
            else:
                root = tempfile.mkdtemp()
                self.import_path(root, base_image)
                shutil.rmtree(root)
        self.remove_container(self.assemble_container)
        self.create_container(self.assemble_container, base_image, command="/bin/freeze",
                              privileged=True, tty=self.tty, volumes_from=self.volumes_from)
        self.install_freeze(self.assemble_container)
        self.start_container(self.assemble_container)

        if self.build_image:
            self.remove_container(self.build_container)
            self.create_container(self.build_container, self.build_image, command=self.build_command,
                                  privileged=True, tty=self.tty, volumes_from=self.build_volumes_from)
            self.start_container(self.build_container)
            if self.platform != self.machine_platform:
                self.config_binfmt(self.build_container, self.platform)
            if self.build_layout:
                self.load_layout(self.build_container, self.build_layout)
            for accept_keyword in self.accept_keywords:
                self.run_cmd(self.build_container, "chroot-{arch}-docker -c \"echo {accept_keyword} >>/etc/portage/package.accept_keywords\"".format(
                    arch=self.arch, accept_keyword=quote(accept_keyword)))
            for mask in self.masks:
                self.run_cmd(self.build_container, "chroot-{arch}-docker -c \"echo {mask} >>/etc/portage/package.mask\"".format(
                    arch=self.arch, mask=quote(mask)))
            for unmask in self.unmasks:
                self.run_cmd(self.build_container, "chroot-{arch}-docker -c \"echo {unmask} >>/etc/portage/package.unmask\"".format(
                    arch=self.arch, unmask=quote(unmask)))
            for use in self.uses:
                self.run_cmd(self.build_container, "chroot-{arch}-docker -c \"echo {use} >>/etc/portage/package.use\"".format(
                    arch=self.arch, use=quote(use)))
            self.run_cmd(self.build_container,
                         "chroot-{arch}-docker -c \"eclean packages && emaint binhost --fix\"".format(arch=self.arch))
            self.run_cmd(self.build_container, "env {env} chroot-{arch}-docker -c \"emerge -kb --binpkg-respect-use=y {packages}\"".format(arch=self.arch,
                                                                                                                                           packages=' '.join(
                                                                                                                                               self.build_dependencies + self.packages),
                                                                                                                                           env=' '.join(['='.join(x) for x in list(self.build_env.items())])))
            package_atoms = ["={}".format(self.run_cmd(self.build_container,
                                                                          "chroot-{arch}-docker -c \"equery list --format=\"\\$cpv\" {package}\" | head -1".format(
                                                                              arch=self.arch, package=package),
                                                                          quiet=True, return_output=True)) for package in self.packages]
            self.run_cmd(self.build_container, "chroot-{arch}-docker -c \"ROOT=/dockeroo-root emerge -OK {packages}\"".format(
                arch=self.arch, packages=' '.join(package_atoms)))
            if self.build_script:
                self.run_script(self.build_container, self.build_script,
                                shell=self.build_script_shell, user=self.build_script_user)
            self.copy_path(self.build_container, self.assemble_container,
                           "/usr/{processor}-{variant}-linux-{abi}/dockeroo-root/".format(processor=self.processor, variant=self.variant, abi=self.abi), dst="/")
            for src, dst in self.copy:
                self.copy_path(self.build_container,
                               self.assemble_container, src, dst=dst)
            self.remove_container(self.build_container)
        if self.layout:
            self.load_layout(self.assemble_container, self.layout,
                             uid=self.layout_uid, gid=self.layout_gid)
        if self.script:
            if self.platform != self.machine_platform:
                self.config_binfmt(self.assemble_container, self.platform)
            self.run_script(self.assemble_container, self.script,
                            shell=self.script_shell, user=self.script_user)
        self.commit_container(self.assemble_container, self.name,
                              command=self.command, user=self.user, labels=self.labels, expose=self.expose, volumes=self.volumes)
        self.remove_container(self.assemble_container)
        self.clean_stale_images()
        return self.mark_completed()

    def update(self):
        if (self.layout and self.is_layout_updated(self.layout)) or \
            (self.build_layout and self.is_layout_updated(self.build_layout)) or \
            (self.build_image and self.is_image_updated(self.build_image)) or \
            (self.base_image and self.is_image_updated(self.base_image)) or \
                not self.images(name=self.name):
            return self.install()
        else:
            return (self.completed, )

    def uninstall(self):
        self.remove_container(self.build_container)
        self.remove_container(self.assemble_container)
        if not self.keep:
            self.remove_image(self.name)
