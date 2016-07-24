
import os
from shellescape import quote
import shutil
import tarfile
import tempfile

from dockeroo import DockerMachineRecipe


class Recipe(DockerMachineRecipe):

    def __init__(self, buildout, name, options):
        super(Recipe, self).__init__(buildout, name, options)

        self.username = self.options.get('username', None)
        self.password = self.options.get('password', None)
        self.registry = self.options.get('registry', 'index.docker.io')
        self.keep = self.options.get('keep', 'false').strip(
            ).lower() in ('true', 'yes', 'on', '1')

    def install(self):
        self.pull_image(self.name,
                        username=self.username,
                        password=self.password,
                        registry=self.registry)
        return self.mark_completed()

    def update(self):
        if self.is_image_updated(self.name) or
            not self.images(name=self.name):
            return self.install()
        return self.mark_completed()

    def uninstall(self):
        if not self.keep:
            self.remove_image(self.name)
