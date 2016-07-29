
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
from subprocess import CalledProcessError

from dockeroo.filters import RecipeFilter


class PatchFilter(RecipeFilter): # pylint: disable=too-few-public-methods
    filter_category = 'patch'

    def __call__(self, path, params=None):
        params = params or {}
        kwargs = {}
        if 'cwd' in params:
            kwargs['cwd'] = params['cwd']
        md5sum = params.get('md5sum', None)
        binary = params.get('command-binary', 'patch')
        options = params.get('command-options', [])
        if '://' in path:
            path = self.recipe.download(path, md5sum=md5sum)
        if not os.path.isabs(path) and 'cwd' in kwargs:
            path = os.path.join(kwargs['cwd'], path)
        kwargs['stdin'] = open(path)
        try:
            self.recipe.call(*([binary] + options), **kwargs)
        except CalledProcessError as exc:
            self.logger.exception("Error applying patch: %s", path)
            return None
        else:
            return path
