
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
from future.moves.urllib.parse import urljoin
from future.moves.urllib.request import pathname2url
from zc.buildout import UserError

from dockeroo.setup.source import BaseSourceRecipe, BaseSourceSubRecipe
from dockeroo.utils import reify

standard_library.install_aliases()


class BaseDownloadSubRecipe(BaseSourceSubRecipe):

    @property
    @reify
    def source_key_processors(self):
        ret = super(BaseDownloadSubRecipe, self).source_key_processors.copy()
        ret.update({
            'url': lambda x: [('url', x.strip())],
            'urls': lambda x: [('url', y) for y in x.split()],
        })
        return ret

    def populate_source(self, source, load_options=True):
        super(BaseDownloadSubRecipe, self).populate_source(source,
                                                           load_options=load_options)
        if 'path' in source:
            if 'url' in source:
                raise UserError(
                    '''You cannot use "url" and "path" at the same time.''')
            if '://' not in source['path'] and os.path.isabs(source['path']):
                source['url'] = urljoin('file:', pathname2url(source['path']))
            else:
                source['url'] = source['path']

    def process_source(self, source):
        pass

    @staticmethod
    def check_source_path(source, key1, key2):
        return os.path.abspath(source[key1]) == os.path.abspath(source[key2])

    def acquire_source(self, source, destkey='working-directory'):
        if 'url' not in source:
            return
        source.update(self.recipe.download(source['url'], params=source))
        destination = source[destkey]
        if source['download-mode'] == 'file':
            if self.options.get_as_bool('unpack', True):
                source['extract-directory'] = self.recipe.extract_archive(
                    source['download-path'], source['working-directory'], params=source)
                if source['extract-directory'] is None:
                    raise UserError('''Unknown source format.''')
                main_directory = self.recipe.guess_main_directory(
                    source['extract-directory'])
                if self.check_source_path(source, 'working-directory', destkey):
                    source['source-directory'] = main_directory
                else:
                    source[
                        'source-directory'] = self.recipe.copy(main_directory, destination)
            else:
                if not self.check_source_path(source, 'download-path', destkey):
                    self.recipe.mkdir(destination)
                    source[
                        'source-directory'] = self.recipe.copy(source['download-path'], destination)
                else:
                    source['source-directory'] = source['download-path']
        elif source['download-mode'] == 'directory':
            source['extract-directory'] = source['download-path']
            source[
                'source-directory'] = self.recipe.guess_main_directory(source['extract-directory'])
            self.copy(source['source-directory'], destination)
        elif source['download-mode'] == 'scm':
            source['extract-directory'] = self.recipe.extract_scm(
                source['repository-type'],
                source['download-path'],
                destination, params=source)
            if source['extract-directory'] is None:
                raise UserError('''Unable to extract repository.''')
            source['source-directory'] = source['extract-directory']
        else:
            raise UserError('''Invalid download mode.''')


class SetupDownloadSubRecipe(BaseDownloadSubRecipe):

    def prepare_source(self, source):
        destkey = 'download-path' if source.get(
            'develop', False) is True else 'location'
        self.acquire_source(source, destkey=destkey)
        self.patch_source(source)
        self.render_template_source(source)

    def process_source(self, source):
        pass


class SetupDownloadRecipe(BaseSourceRecipe):
    """
    A recipe to download a remote package or to copy a local package.

    Example:

        >>> with buildout_test(
        ... '''
        ... [buildout]
        ... parts = part
        ... find-links =
        ...     https://pypi.python.org/simple/future/
        ...     https://pypi.python.org/simple/setuptools/
        ...     https://pypi.python.org/simple/shellescape/
        ...     https://pypi.python.org/simple/tzlocal/
        ...
        ... [part]
        ... recipe = dockeroo:setup.download
        ... url = %(server)sdata/package-0.0.0.tar.gz
        ... patches =
        ...     patches/configure.patch
        ...     patches/Makefile.dist.patch
        ... ''' % dict(server=server_url)) as b:
        ...    print_(b.run(), end='')
        Installing part.
        dockeroo: Downloading <URL>
        dockeroo: Applying patch: "patches/configure.patch"
        dockeroo: patching file configure
        dockeroo: Applying patch: "patches/Makefile.dist.patch"
        dockeroo: patching file Makefile.dist

    git clone and update:

        >>> with buildout_test(
        ... '''
        ... [buildout]
        ... parts = part
        ... download-cache = ${buildout:directory}/downloads
        ... find-links =
        ...     https://pypi.python.org/simple/future/
        ...     https://pypi.python.org/simple/setuptools/
        ...     https://pypi.python.org/simple/shellescape/
        ...     https://pypi.python.org/simple/tzlocal/
        ...
        ... [part]
        ... recipe = dockeroo:setup.download
        ... url = git+https://github.com/buildout/buildout.git
        ... verbose = true
        ... repository-subpath = doc
        ... ''') as b:
        ...    mkdir(sample_buildout, 'downloads')
        ...    print_(b.run(), end='')
        ...    print_(b.run(), end='')
        Installing part.
        dockeroo: Downloading <URL>
        dockeroo: Running command: git clone -q --bare "<URL>" "<PATH>"
        dockeroo: Running command: git read-tree "master"
        dockeroo: Running command: git checkout-index -q -a -f --prefix="<PATH>"
        Updating part.
        dockeroo: Downloading <URL>
        dockeroo: Running command: git fetch -q origin
        dockeroo: Running command: git checkout-index -q -a -f --prefix="<PATH>"
    """
    subrecipe_class = SetupDownloadSubRecipe
