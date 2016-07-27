
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
from tempfile import mkdtemp

from future import standard_library
from future.moves.urllib.parse import urlparse, ParseResult, parse_qs
from zc.buildout import UserError

from dockeroo.filters import RecipeFilter
from dockeroo.filters.scm import GitRecipeFilterMixin
from dockeroo.utils import quote, string_as_bool

standard_library.install_aliases()

REPO_TYPES = {
    'git': ('git', 'git'),
    'git+http': ('git', 'http'),
    'git+https': ('git', 'https'),
}


class ScmDownloadFilter(RecipeFilter, GitRecipeFilterMixin):
    filter_category = 'download'

    def __call__(self, url, params=None, force=False): # pylint: disable=too-many-locals
        download = self.recipe.download_manager
        urlobj = urlparse(url)
        fragment_params = parse_qs(urlobj.fragment)
        params.update(fragment_params)
        try:
            repo_type, repo_scheme = REPO_TYPES[urlobj.scheme]
        except KeyError:
            return None
        urlobj = ParseResult(scheme=repo_scheme,
                             netloc=urlobj.netloc,
                             path=urlobj.path,
                             params=urlobj.params,
                             query=urlobj.query,
                             fragment='')
        func = {
            'git': self.download_git,
        }[repo_type]
        if download.download_cache:
            base_path = download.download_cache
        else:
            base_path = mkdtemp(prefix='buildout-')
        if not os.path.exists(base_path):
            self.recipe.mkdir(base_path)
        path = os.path.join(base_path, download.filename(url))
        self.logger.info('''Downloading {}'''.format(urlobj.geturl()))
        ret = {
            'download-path': path,
            'download-mode': 'scm',
            'repository-type': repo_type,
        }
        ret.update(dict([('repository-{}'.format(k), v) for k, v in list(fragment_params.items())]))
        result = func(urlobj, path, params=params or {}, force=force)
        if isinstance(result, dict):
            ret.update(result)
        return ret

    def download_git(self, urlobj, path, params=None, force=False): # pylint: disable=unused-argument
        url = urlobj.geturl()
        params = params or {}
        recursive = params.get('repository-recursive', False)
        verbose = string_as_bool(params.get('verbose', False))
        if not os.path.exists(path):
            if self.recipe.offline:
                raise UserError('''Couldn't download "{}" in offline mode.'''.format(url))
            command_args = ['--bare']
            if recursive:
                command_args.append('--recursive')
            command_args += [quote(format(url)), quote(path)]
            self.git_cmd('clone', command_args, verbose=verbose)
        else:
            command_args = ['origin']
            self.git_cmd('fetch', command_args, verbose=verbose, env={
                'GIT_DIR': path,
            })
