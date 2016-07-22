
import time

from zc.buildout import UserError
from zc.buildout.download import Download

from dockeroo import DockerMachineRecipe, Archive
from dockeroo.utils import merge


class Recipe(DockerMachineRecipe):

    def __init__(self, buildout, name, options):
        super(Recipe, self).__init__(buildout, name, options)

        self.image_name = self.options.get('name', self.name)
        if ':' not in self.image_name:
            self.image_name += ':latest'
        self.source = self.options['source']
        self.build_args = dict([y for y in [x.strip().split('=', 1) for x in self.options.get('build-args', '').split('\n')] if y[0]])
        self.keep = self.options.get('keep', 'false').strip(
            ).lower() in ('true', 'yes', 'on', '1')

    def install(self):
        if not self.images(self.image_name):
            self.build_dockerfile(self.image_name,
                                  self.source,
                                  **self.build_args)
        return self.mark_completed()

    def update(self):
        return self.install()

    def uninstall(self):
        if not self.keep:
            self.remove_image(self.image)
