
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
        self.container = self.options.get('container', self.name)
        self.user = self.options.get('user', None)
        self.layout = self.options.get('layout', None)
        self.tty = self.options.get('tty', 'false').strip(
        ).lower() in ('true', 'yes', 'on', '1')
        self.env = dict(filter(lambda y: y[0], map(lambda x: x.strip().split(
            '='), self.options.get('env', '').split('\n'))))
        self.ports = dict(filter(lambda y: y[0], map(lambda x: x.strip().split(
            ':'), self.options.get('ports', '').split('\n'))))
        self.links = dict(filter(lambda y: y[0], map(lambda x: x.strip().split(
            ':'), self.options.get('links', '').split('\n'))))
        self.networks = filter(None, map(lambda x: x.strip(), self.options.get('networks', '').split('\n')))
        self.network_aliases = filter(None, map(lambda x: x.strip(), self.options.get('network-aliases', '').split('\n')))
        self.volumes = filter(lambda y: y[0], map(lambda x: x.strip().split(':', 1),
                                                  self.options.get('volumes', '').split('\n')))
        self.volumes_from = self.options.get('volumes-from', None)
        self.script_shell = self.options.get('script-shell', self.shell)
        self.script_user = self.options.get('script-user', None)
        self.script = "#!{}\n{}".format(self.script_shell, '\n'.join(filter(
            None, map(lambda x: x.strip(), self.options.get('script').replace('$$', '$').split('\n'))))) \
            if self.options.get('script', None) is not None else None

    def install(self):
        self.remove_container(self.container)
        self.create_container(self.container, self.image, command=self.command, run=True,
                              tty=self.tty, volumes=self.volumes, volumes_from=self.volumes_from,
                              user=self.user, env=self.env, ports=self.ports,
                              networks=self.networks, links=self.links, network_aliases=self.network_aliases)
        self.options['ip-address'] = self.get_container_ip_address(self.container)
        if self.layout:
            self.load_layout(self.container, self.layout)
        if self.script:
            self.run_script(self.container, self.script,
                            shell=self.script_shell, user=self.script_user)
        return self.mark_completed()

    def update(self):
        if self.is_image_updated(self.image):
            return self.install()
        else:
            if (self.layout and self.is_layout_updated(self.layout)):
                self.load_layout(self.container, self.layout)
                if self.script:
                    self.run_script(self.container, self.script,
                                    shell=self.script_shell, user=self.script_user)
            return self.mark_completed()

    def uninstall(self):
        self.remove_container(self.container)
