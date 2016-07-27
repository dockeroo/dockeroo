
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

from future import standard_library
from future.moves.urllib.parse import urlparse
from future.moves.urllib.request import url2pathname
from zc.buildout import UserError
from zc.buildout.download import check_md5sum

from dockeroo.filters import RecipeFilter

standard_library.install_aliases()


class FileDownloadFilter(RecipeFilter):
    filter_category = 'download'

    def __call__(self, url, params=None, force=False):
        urlobj = urlparse(url)
        params = params or {}
        md5sum = params.get('md5sum', None)
        try:
            func = {
                'http': self.download_buildout,
                'https': self.download_buildout,
                'file': self.download_local,
            }[urlobj.scheme]
        except KeyError:
            return None
        return func(urlobj, md5sum=md5sum, force=force)

    def download_buildout(self, urlobj, md5sum=None, force=False):
        download = self.recipe.download_manager
        url = urlobj.geturl()
        if download.download_cache and force is False:
            path = os.path.join(download.download_cache, download.filename(url))
            if os.path.isfile(path) and check_md5sum(path, md5sum):
                return {
                    'download-path': path,
                    'download-mode': 'file',
                }
        if self.recipe.offline:
            raise UserError('''Couldn't download "{}" in offline mode.'''.format(url))
        path, _ = download(url, md5sum=md5sum)
        return {
            'download-path': path,
            'download-mode': 'file',
        }

    def download_local(self, urlobj, md5sum=None, force=False): # pylint: disable=unused-argument,no-self-use
        path = url2pathname(urlobj.path)
        if not os.path.exists(path):
            raise UserError('''Path "{}" doesn't exist.'''.format(path))
        if md5sum is not None:
            if not os.path.isfile(path):
                raise UserError(
                    'You cannot use option "md5sum" on non-file path "{}".'.format(path))
            if check_md5sum(path, md5sum):
                return {
                    'download-path': path,
                    'download-mode': 'file',
                }
        if os.path.isfile(path):
            return {
                'download-path': path,
                'download-mode': 'file',
            }
        elif os.path.isdir(path):
            return {
                'download-path': path,
                'download-mode': 'directory',
            }
        else:
            raise UserError('''Path "{}" is not a file nor a directory.'''.format(path))
