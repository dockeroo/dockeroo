
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


from zc.buildout import UserError

from dockeroo.setup.download import BaseDownloadSubRecipe, SetupDownloadRecipe


class SetupPythonScriptSubRecipe(BaseDownloadSubRecipe):

    def initialize(self):
        super(SetupPythonScriptSubRecipe, self).initialize()
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

    def process_source(self, source):
        pass


class SetupPythonScriptRecipe(SetupDownloadRecipe):
    """
    A recipe to run an installation script.

    Example:

        >>> with buildout_test('''
        ... [buildout]
        ... index = http://pypi.python.org/simple/
        ... parts = part
        ...
        ... [part]
        ... recipe = dockeroo:setup.python-script
        ... script =
        ... ''') as b:
        ...     print_(b.run(), end='')
        Installing part.
    """

    subrecipe_class = SetupPythonScriptSubRecipe
