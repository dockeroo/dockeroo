
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016, Giacomo Cariello. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
from subprocess import Popen, PIPE

from zc.buildout import UserError

from dockeroo.setup.download import BaseDownloadSubRecipe, SetupDownloadRecipe


class SetupShellScriptSubRecipe(BaseDownloadSubRecipe):
    def initialize(self):
        super(SetupShellScriptSubRecipe, self).initialize()
        if 'install-script' in self.options:
            self.install_script = self.options.get('install-script')
        elif 'script' in self.options:
            self.install_script = self.options.get('script')
        elif not hasattr(self, 'install_script'):
            raise UserError(
                '''You must provide a "script" or "install-script" field.''')

        if 'update-script' in self.options:
            self.update_script = self.options.get('update-script')
        elif 'script' in self.options:
            self.update_script = self.options.get('script')
        else:
            self.update_script = None

        self.script_shell = self.options.get('script-shell', self.recipe.shell)
        self.script_env = dict([y for y in [x.strip().split(
            '=') for x in self.options.get('script-env', '').splitlines()] if y[0]])
        self.script = "#!{}\n{}".format(
            self.script_shell,
            '\n'.join([_f for _f in \
                [x.strip() for x in \
                 self.options.get('script').replace('$$', '$').splitlines()]
                       if _f])) \
            if self.options.get('script', None) is not None else None


    def run_script(self, script):
        proc = Popen(self.script_shell, stdin=PIPE, stderr=PIPE, close_fds=True)
        proc.stdin.write(script)
        proc.stdin.close()
        if proc.wait() != 0:
            raise ExternalProcessError(
                "Error running script \"{}\"".format(self.name), proc)

    def process_source(self, source):
        pass

    def install(self):
        super(SetupShellScriptSubRecipe, self).install()
        self.run_script(self.install_script)

    def upgrade(self):
        super(SetupShellScriptSubRecipe, self).upgrade()
        self.run_script(self.update_script)


class SetupShellScriptRecipe(SetupDownloadRecipe):
    """
    A recipe to run an installation script.

    Example:
        >>> with buildout_test('''
        ... [buildout]
        ... index = http://pypi.python.org/simple/
        ... parts = part
        ...
        ... [part]
        ... recipe = dockeroo:setup.shell-script
        ... script = echo "HELLO."
        ... ''') as b:
        ...     print_(b.run(), end='')
        Installing part.
        HELLO.
    """

    subrecipe_class = SetupShellScriptSubRecipe
