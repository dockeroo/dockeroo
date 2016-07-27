
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

from dockeroo.filters import RecipeFilter
from dockeroo.filters.scm import GitRecipeFilterMixin
from dockeroo.utils import quote, string_as_bool


class ScmExtractFilter(RecipeFilter, GitRecipeFilterMixin):
    filter_category = 'extract.scm'

    def __call__(self, repo_type, path, extract_dir, params=None):
        if not os.path.isdir(path):
            return None
        try:
            func = {
                'git': self.extract_git,
            }[repo_type]
        except Exception: # pylint: disable=broad-except
            return None
        else:
            func(path, extract_dir, params=params or {})
            return extract_dir

    def extract_git(self, src, dst, params=None):
        params = params or {}
        rev = params.get('repository-rev', None)
        branch = params.get('repository-branch', None)
        subpath = params.get('repository-subpath', None)
        if branch is not None:
            tree_spec = branch
        elif rev is not None:
            tree_spec = rev
        else:
            tree_spec = 'master'
        if subpath is not None:
            tree_spec = "{}:{}".format(tree_spec, subpath)
        verbose = string_as_bool(params.get('verbose', False))
        self.recipe.mkdir(dst)
        index_file = os.path.join(dst, '.git-index')
        if not os.path.exists(index_file):
            self.git_cmd('read-tree', [quote(tree_spec)], env={
                'GIT_INDEX_FILE': index_file,
                'GIT_DIR': src,
                'GIT_WORK_TREE': dst,
            }, verbose=True)
        self.git_cmd('checkout-index', ['-a', '-f', '--prefix={}'.format(quote(dst + '/'))], env={
            'GIT_INDEX_FILE': index_file,
            'GIT_DIR': src,
            'GIT_WORK_TREE': dst,
        }, verbose=verbose)
