
import os
from shellescape import quote
import shutil
import tarfile
import tempfile

from dockeroo import DockerMachineRecipe


class Recipe(DockerMachineRecipe):

    def __init__(self, buildout, name, options):
        super(Recipe, self).__init__(buildout, name, options)

        self.image = self.options['image']
        self.command = self.options.get('command', None)
        self.user = self.options.get('user', None)
        self.layout = self.options.get('layout', None)
        self.tty = self.options.get('tty', 'false').strip(
        ).lower() in ('true', 'yes', 'on', '1')
        self.env = dict([y for y in [x.strip().split(
            '=') for x in self.options.get('env', '').split('\n')] if y[0]])
        self.ports = dict([y for y in [x.strip().split(
            ':') for x in self.options.get('ports', '').split('\n')] if y[0]])
        self.links = dict([y for y in [x.strip().split(
            ':') for x in self.options.get('links', '').split('\n')] if y[0]])
        self.networks = [_f for _f in [x.strip() for x in self.options.get('networks', '').split('\n')] if _f]
        self.network_aliases = [_f for _f in [x.strip() for x in self.options.get('network-aliases', '').split('\n')] if _f]
        self.volumes = [y for y in [x.strip().split(':', 1) for x in self.options.get('volumes', '').split('\n')] if y[0]]
        self.volumes_from = self.options.get('volumes-from', None)
        self.script_shell = self.options.get('script-shell', self.shell)
        self.script_user = self.options.get('script-user', None)
        self.script = "#!{}\n{}".format(self.script_shell, '\n'.join([_f for _f in [x.strip() for x in self.options.get('script').replace('$$', '$').split('\n')] if _f])) \
            if self.options.get('script', None) is not None else None
        self.start = self.options.get('start', 'true').strip(
        ).lower() in ('true', 'yes', 'on', '1')

    def install(self):
        self.remove_container(self.name)
        self.create_container(self.name, self.image, command=self.command, run=False,
                              tty=self.tty, volumes=self.volumes, volumes_from=self.volumes_from,
                              user=self.user, env=self.env, ports=self.ports,
                              networks=self.networks, links=self.links, network_aliases=self.network_aliases)
        if self.layout:
            self.load_layout(self.name, self.layout)
        if not self.start:
            self.options.pop('ip-address', None)
            return self.mark_completed()
        self.start_container(self.name)
        self.options['ip-address'] = self.get_container_ip_address(self.name)
        if self.script:
            self.run_script(self.name, self.script,
                            shell=self.script_shell, user=self.script_user)
        return self.mark_completed()

    def update(self):
        if self.is_image_updated(self.image):
            return self.install()
        else:
            if (self.layout and self.is_layout_updated(self.layout)):
                self.load_layout(self.name, self.layout)
                if self.script:
                    self.run_script(self.name, self.script,
                                    shell=self.script_shell, user=self.script_user)
            return self.mark_completed()

    def uninstall(self):
        self.remove_container(self.name)
