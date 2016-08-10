
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
from string import Template as StringTemplate

from zc.buildout import UserError

from dockeroo import BaseSubRecipe, BaseGroupRecipe
from dockeroo.utils import string_as_bool


class SetupTemplateSubRecipe(BaseSubRecipe):

    def initialize(self):
        super(SetupTemplateSubRecipe, self).initialize()
        self.content = self.options.get('content', None)
        self.input_path = self.options.get('input-path', None)
        self.options.setdefault('output-path', os.path.join(self.location, self.name))
        self.output_path = self.options.get('output-path')
        if bool(self.content) == bool(self.input_path):
            if self.content:
                raise UserError('''You cannot use "content" and "input-path" at the same time.''')
            else:
                raise UserError('''You shall specify a least "content" or "input-path".''')

    def install(self):
        if self.input_path is not None:
            with open(self.input_path, 'rb') as input_path_fh:
                output = StringTemplate(input_path_fh.read()).substitute(**self.options.copy())
        else:
            output = self.content
        self.recipe.mkdir(os.path.dirname(self.output_path))
        with open(self.output_path, 'wb') as output_path_fh:
            output_path_fh.write(output)
        return self.mark_completed()

    def update(self):
        completed_mtime = os.stat(self.completed).st_mtime
        if not os.path.exists(self.output_path) or \
            os.stat(self.output_path).st_mtime > completed_mtime:
            self.install()


class SetupTemplateRecipe(BaseGroupRecipe):
    """
    A recipe to run an installation script.

    Example:

        >>> import os
        >>> with buildout_test('''
        ... [buildout]
        ... index = http://pypi.python.org/simple/
        ... parts = part
        ...
        ... [part]
        ... recipe = dockeroo:setup.template
        ... test-string = HELLO
        ... content = ${:test-string}
        ... output-path = ${buildout:directory}/test.txt
        ... ''') as b:
        ...     print_(b.run(), end='')
        ...     print_(open(os.path.join(sample_buildout, 'test.txt'), 'rb').read())
        Installing part.
        HELLO
    """

    subrecipe_class = SetupTemplateSubRecipe
