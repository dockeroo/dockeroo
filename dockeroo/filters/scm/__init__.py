
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


from builtins import object # pylint: disable=redefined-builtin
from subprocess import CalledProcessError
from zc.buildout import UserError


class GitRecipeFilterMixin(object):
    def git_cmd(self, operation, args, ignore_errnos=None, verbose=False, **kwargs):
        cmd_path = self.recipe.options.get(
            'git-binary', default=self.recipe.buildout.get('git-binary', default='git'))
        command = [cmd_path, operation]
        if not verbose:
            command.append('-q')
        command += args
        command_line = ' '.join(command)
        self.logger.info('Running command: %s', command_line)
        if 'env' not in kwargs:
            kwargs['env'] = {}
        kwargs['env'].setdefault('LC_ALL', 'C')
        kwargs['shell'] = True
        kwargs['ignore_errnos'] = ignore_errnos or []
        try:
            self.recipe.call(command_line, **kwargs)
        except CalledProcessError as exc:
            raise UserError('Command: "{}" failed with status: {}'.format(exc.cmd, exc.returncode))
