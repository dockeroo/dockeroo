
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
        self.username = self.options['username']
        self.password = self.options['password']
        self.tag = self.options.get('tag', 'latest')
        self.registry = self.options.get('registry', 'index.docker.io')

    def install(self):
        self.push_image(self.image,
                        self.username,
                        self.password,
                        tag=self.tag,
                        registry=self.registry)
        return self.mark_completed()

    def update(self):
        if self.is_image_updated(self.image):
            return self.install()

    def uninstall(self):
        pass
