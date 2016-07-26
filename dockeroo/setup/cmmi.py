
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


from future import standard_library
standard_library.install_aliases()
import shlex

from dockeroo.setup.download import BaseDownloadSubRecipe, Recipe as DownloadRecipe
from dockeroo.utils import FALSE_SET


class SubRecipe(BaseDownloadSubRecipe):

    def update(self):
        pass

    def process_source(self, source):
        if self.options.get_as_bool('build', False) is False:
            return
        preconfigure_command = self.options.get('preconfigure-command', None)
        if preconfigure_command is not None:
            preconfigure_command = shlex.split(preconfigure_command)
            self.logger.info("Preconfiguring with: {}".format(
                ' '.join(preconfigure_command)))
            self.recipe.call(
                *preconfigure_command, cwd=source['source-directory'], env=self.environment, shell=True)
        configure_command = self.options.get('configure-command', None)
        if configure_command is None:
            configure_options = shlex.split(
                self.options.get('configure-options', ''))
            configure_command = [
                "./configure", "--prefix={}".format(self.location)] + configure_options
        elif configure_command.strip().lower() in FALSE_SET:
            configure_command = None
        else:
            configure_command = shlex.split(configure_command)
        if configure_command:
            self.logger.info('''Configuring with: "{}"'''.format(
                ' '.join(configure_command)))
            self.recipe.call(
                *configure_command, cwd=source['source-directory'], env=self.environment, shell=True)
        make_binary = self.options.get('make-binary', None)
        if make_binary is None:
            make_binary = 'make'
        elif make_binary.strip().lower() in FALSE_SET:
            make_binary = None
        else:
            make_binary = make_binary.strip()
        if make_binary is not None:
            make_command = [make_binary]
            make_targets = shlex.split(self.options.get('make-targets', ''))
            make_command.extend(make_targets)
            make_options = shlex.split(self.options.get('make-options', ''))
            make_command.extend(make_options)
            self.logger.info('''Building with: "{}"'''.format(
                ' '.join(make_command)))
            self.recipe.call(
                *make_command, cwd=source['source-directory'], env=self.environment, shell=True)
        make_install_binary = self.options.get('make-install-binary', None)
        if make_install_binary is None:
            make_install_binary = make_binary
        elif make_install_binary.strip().lower() in FALSE_SET:
            make_install_binary = None
        else:
            make_install_binary = make_install_binary.strip()
        if make_install_binary is not None:
            make_install_command = [make_install_binary]
            make_install_targets = self.options.get(
                'make-install-targets', None)
            if make_install_targets is None:
                make_install_targets = ['install']
            else:
                make_install_targets = shlex.split(make_install_targets)
            make_install_command.extend(make_install_targets)
            make_install_options = self.options.get(
                'make-install-options', None)
            if make_install_options is None:
                make_install_options = make_options
            else:
                make_install_options = shlex.split(make_install_options)
            make_install_command.extend(make_install_options)
            self.logger.info('''Installing with: "{}"'''.format(
                ' '.join(make_install_command)))
            self.recipe.call(
                *make_install_command, cwd=source['source-directory'], env=self.environment, shell=True)


class Recipe(DownloadRecipe):
    """
    A recipe to configure, make and make install:

    Example:

        >>> with buildout_test('''
        ... [buildout]
        ... parts = part
        ... find-links =
        ...     https://pypi.python.org/simple/decorator/
        ...     https://pypi.python.org/simple/future/
        ...     https://pypi.python.org/simple/setuptools/
        ...     https://pypi.python.org/simple/shellescape/
        ...     https://pypi.python.org/simple/tzlocal/
        ... 
        ... [part]
        ... recipe = dockeroo:build.cmmi
        ... url = %(server)sdata/package-0.0.0.tar.gz
        ... ''' % dict(server=server_url)) as b:
        ...     print_(b.run(), end='')
        Installing part.
        dockeroo: Downloading <URL>
        dockeroo: Configuring with: "./configure --prefix=<PATH>"
        dockeroo: configure
        dockeroo: Building with: "make"
        dockeroo: building package
        dockeroo: Installing with: "make install"
        dockeroo: building package
    """
    subrecipe_class = SubRecipe

    def __init__(self, buildout, name, options):
        super(Recipe, self).__init__(buildout, name, options)
        self.options.setdefault('build', 'true')
