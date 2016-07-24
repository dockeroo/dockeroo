
import os
from shellescape import quote
import shutil
import tarfile
import tempfile

from dockeroo import DockerMachineRecipe


class Recipe(DockerMachineRecipe):

    def __init__(self, buildout, name, options):
        super(Recipe, self).__init__(buildout, name, options)

        self.keep = self.options.get('keep', 'false').strip(
        ).lower() in ('true', 'yes', 'on', '1')
        self.internal = self.options.get('internal', 'false').strip(
        ).lower() in ('true', 'yes', 'on', '1')
        self.ipv6 = self.options.get('ipv6', 'false').strip(
        ).lower() in ('true', 'yes', 'on', '1')

        self.driver = self.options.get('driver', 'bridge')
        self.gateway = self.options.get('gateway', None)
        self.subnet = self.options.get('subnet', None)
        self.ip_range = self.options.get('ip-range', None)

    def install(self):
        self.create_network(self.name,
                            driver=self.driver,
                            gateway=self.gateway,
                            subnet=self.subnet,
                            ip_range=self.ip_range,
                            internal=self.internal,
                            ipv6=self.ipv6)
        return ()

    def update(self):
        pass

    def uninstall(self):
        if not self.keep:
            self.remove_network(self.name)
