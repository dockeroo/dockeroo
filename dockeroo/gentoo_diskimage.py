
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

        self.build_command = self.options.get('build-command', "/bin/freeze")
        self.build_container = "{}_build".format(self.name)
        self.build_image = self.options['build-image']
        self.build_volumes_from = self.options.get('build-volumes-from', None)
        self.build_script_user = self.options.get('build-script-user', None)
        self.build_script_shell = self.options.get(
            'build-script-shell', self.shell)
        self.prepare_script = "#!{}\n{}".format(self.build_script_shell,
                                                '\n'.join(filter(None, map(lambda x: x.strip(), self.options.get('prepare-script').replace('$$', '$').split('\n'))))) if self.options.get('prepare-script', None) is not None else None
        self.build_script = "#!{}\n{}".format(self.build_script_shell,
                                              '\n'.join(filter(None, map(lambda x: x.strip(), self.options.get('build-script').replace('$$', '$').split('\n'))))) if self.options.get('build-script', None) is not None else None
        self.build_root = self.options['build-root']
        self.base_image = self.options['base-image']
        self.image_file = self.options['image-file']

        self.platform = self.options.get('platform', self.machine_platform)
        self.arch = self.options.get('arch', self.platform)
        self.tty = self.options.get('tty', 'false').strip(
        ).lower() in ('true', 'yes', 'on', '1')

    def install(self):
        self.location = self.options.get("location", os.path.join(
            self.buildout["buildout"]["parts-directory"], self.name))
        self.remove_container(self.build_container)
        self.create_container(self.build_container, self.build_image, command=self.build_command,
                              privileged=True, tty=self.tty, volumes_from=self.build_volumes_from)
        self.start_container(self.build_container)
        if self.platform != self.machine_platform:
            self.config_binfmt(self.build_container, self.platform)
        if self.prepare_script:
            self.run_script(self.build_container, self.prepare_script,
                            shell=self.build_script_shell, user=self.build_script_user)
        self.copy_image_to_container(
            self.base_image, self.build_container, "/", dst=self.build_root)
        if self.build_script:
            self.run_script(self.build_container, self.build_script,
                            shell=self.build_script_shell, user=self.build_script_user)
        self.export_files(self.build_container, self.image_file, self.location)
        self.remove_container(self.build_container)
        self.clean_stale_images()
        return self.mark_completed()

    def update(self):
        if self.is_image_updated(self.build_image) or \
                self.is_image_updated(self.base_image):
            return self.install()
        else:
            return (self.completed, )

    def uninstall(self):
        self.remove_container(self.build_container)
