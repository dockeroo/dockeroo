
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
        self.options['name'] = self.options.get('name', self.name)

    def install(self):
        self.create_volume(self.options['name'])
        return ()

    def update(self):
        pass

    def uninstall(self):
        if not self.keep:
            self.remove_volume(self.options['name'])
