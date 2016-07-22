
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

        self.container_from = self.options['container-from']
        self.container_to = self.options['container-to']
        self.paths = [merge([None, None], y.split()[:2]) for y in [f for f in [x.strip() for x in self.options.get('paths', '').split('\n')] if f]]

    def install(self):
        for src, dst in self.paths:
            self.copy_path(self.container_from,
                           self.container_to, src, dst=dst)

    def update(self):
        pass

    def uninstall(self):
        pass
