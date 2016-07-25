
import os
from shellescape import quote
import shutil
import tarfile
import tempfile

from dockeroo import DockerRecipe


class Recipe(DockerRecipe):

    def __init__(self, buildout, name, options):
        super(Recipe, self).__init__(buildout, name, options)

        self.keep = self.options.get('keep', 'false').strip(
        ).lower() in ('true', 'yes', 'on', '1')

    def install(self):
        self.create_volume(self.name)
        return self.mark_completed()

    def update(self):
        return self.install()

    def uninstall(self):
        if not self.keep:
            self.remove_volume(self.name)
