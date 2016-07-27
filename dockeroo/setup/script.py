
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
from zc.buildout.easy_install import default_index_url, _get_index as get_index

from dockeroo.setup.download import BaseDownloadSubRecipe, SetupDownloadRecipe
from dockeroo.utils import reify


class SetupScriptSubRecipe(BaseDownloadSubRecipe):

    @property
    @reify
    def index_url(self):
        return self.options.get('index',
                                self.recipe.buildout['buildout'].get('index',
                                                                     default_index_url))

    @property
    @reify
    def find_links_urls(self):
        return self.options.get('find-links',
                                self.recipe.buildout['buildout'].get('find-links', '')).split()

    def initialize(self):
        super(SetupScriptSubRecipe, self).initialize()
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
        self.index = get_index(self.index_url, self.find_links_urls)

    def process_source(self, source):
        pass


class SetupScriptRecipe(SetupDownloadRecipe):
    """
    A recipe to run an installation script.

    Example:
        >>> with buildout_test('''
        ... [buildout]
        ... index = http://pypi.python.org/simple/
        ... parts = part
        ...
        ... [part]
        ... recipe = dockeroo:setup.script
        ... script =
        ... ''') as b:
        ...     print_(b.run(), end='')
        Installing part.
    """

    subrecipe_class = SetupScriptSubRecipe
