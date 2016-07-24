
import time

from zc.buildout import UserError
from zc.buildout.download import Download

from dockeroo import DockerMachineRecipe, Archive
from dockeroo.utils import merge


class Recipe(DockerMachineRecipe):

    def __init__(self, buildout, name, options):
        super(Recipe, self).__init__(buildout, name, options)
        if ':' not in self.name:
            self.name += ':latest'

        self.command = self.options.get("command", "/bin/freeze")
        self.commit = self.options.get('commit', 'false').strip(
        ).lower() in ('true', 'yes', 'on', '1')
        self.container = self.options.get('container',
            "{}_bootstrap".format(self.name.replace(':', '_')))
        self.keep = self.options.get('keep', 'false').strip(
        ).lower() in ('true', 'yes', 'on', '1')
        self.layout = self.options.get('layout', None)
        self.crossdev_platform = self.options.get(
            'crossdev-platform', self.machine_platform)
        self.script = "#!{}\n{}".format(self.shell,
                                        '\n'.join([_f for _f in [x.strip() for x in self.options.get('script').replace('$$', '$').split('\n')] if _f])) if self.options.get('script', None) is not None else None
        self.tty = self.options.get('tty', 'false').strip(
        ).lower() in ('true', 'yes', 'on', '1')
        self.archives = []
        for url, prefix, md5sum in [merge([None, None, None], x.split())[:3] for x in [_f for _f in [x.strip() for x in self.options.get('archives', self.options.get('archive', '')).split('\n')] if _f]]:
            if prefix == '/':
                prefix = None
            self.archives.append(
                Archive(url=url, prefix=prefix, md5sum=md5sum))
        self.volumes = [y for y in [x.strip().split(
            ':', 1) for x in self.options.get('volumes', '').split('\n')] if y[0]]
        self.volumes_from = self.options.get('volumes-from', None)

    def install(self):
        if not any([x for x in self.images() if self.name == x['image']]):
            if not self.archives:
                raise UserError(
                    "Image does not exist and no source specified.")
            for archive in self.archives:
                archive.download(self.buildout)
            self.import_archives(self.name, *self.archives)

        if not self.containers(all=True, name=self.container):
            self.create_container(self.container, self.name, command=self.command, privileged=True,
                                  tty=self.tty, volumes=self.volumes, volumes_from=self.volumes_from)
        # else:
        #    raise RuntimeError("Container \"{}\" already exists".format(self.container))

        self.install_freeze(self.container)

        if self.layout:
            self.load_layout(self.container, self.layout)

        self.start_container(self.container)

        if self.script:
            if self.crossdev_platform != self.machine_platform:
                self.config_binfmt(self.container, self.crossdev_platform)
            self.run_script(self.container, self.script)

        if self.commit:
            self.commit_container(self.container, self.name)
            self.remove_container(self.container)
            self.clean_stale_images()

        return self.mark_completed()

    def update(self):
        if self.layout and self.is_layout_updated(self.layout):
            return self.install()
        else:
            return (self.completed, )

    def uninstall(self):
        self.remove_container(self.container)
        if not self.keep:
            self.remove_image(self.name)
