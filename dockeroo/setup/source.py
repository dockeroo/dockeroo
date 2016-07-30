
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


from collections import defaultdict
import os
import random
import string

from builtins import range # pylint: disable=redefined-builtin
from future import standard_library
from past.builtins import basestring # pylint: disable=redefined-builtin

from dockeroo import BaseGroupRecipe, BaseSubRecipe
from dockeroo.utils import reify

standard_library.install_aliases()


class BaseSourceSubRecipe(BaseSubRecipe):

    def initialize(self):
        super(BaseSourceSubRecipe, self).initialize()
        self.sources = self.recipe.sources[self.group]
        options = self.options.copy()
        for option_name, processor in self.source_key_processors.items():
            if option_name in options:
                option = options.pop(option_name)
                for source_option, source_key in processor(option):
                    self.sources.append({
                        source_option: source_key
                    })
        self.common_options = {}
        for option_name, processor in self.source_option_processors.items():
            if option_name in options:
                option = options.pop(option_name)
                if callable(processor):
                    self.common_options[option_name] = processor(option)
        if getattr(self, 'allowed_options', None) is not None:
            options = dict([(k, v) for k, v in options.items() if k in self.allowed_options])
        self.common_options.update(options)
        for source in self.sources:
            self.populate_source(source)

    def install_sources(self):
        for source in self.sources:
            self.prepare_source(source)
        for source in self.sources:
            self.process_source(source)

    def install(self):
        self.install_sources()

    def update(self):
        self.install_sources()

    @classmethod
    def resolve_stage(cls, option, stage=None):
        return "{}-{}".format(stage, option) if stage is not None else option

    @property
    @reify
    def source_key_processors(self):
        return {
            'path': lambda x: [('path', x.strip())],
            'paths': lambda x: [('path', y) for y in x.split()],
        }

    @property
    @reify
    def source_option_processors(self):
        return {
            'md5sum': lambda x: x.strip().lowercase() if isinstance(x, basestring) else x,
        }

    @property
    @reify
    def allowed_options(self):
        return [
            'executable',
            'working-directory',
            'patches',
            'patch-options',
            'patch-binary',
            'template-sources',
        ]

    def prepare_source(self, source):
        self.recipe.mkdir(source['working-directory'])
        self.acquire_source(source, destkey='download-path'
                            if source.get('develop', False) is True else 'working-directory')
        self.patch_source(source)
        self.render_template_source(source)

    def populate_source(self, source, load_options=True):
        if load_options:
            source.update(self.common_options)
        source.setdefault('executable', self.executable)
        source.setdefault(
            'working-directory',
            os.path.join(
                self.working_directory,
                "tmp{}".format(''.join(random.choice(string.ascii_letters + string.digits) \
                    for _ in range(8)))))
        if self.location is not None:
            source['location'] = self.location

    def acquire_source(self, source, destkey='working-directory'):
        raise NotImplementedError

    def patch_source(self, source, cwdkey='source-directory', stage=None):
        option = self.resolve_stage('patches', stage=stage)
        if option in source:
            patches = [x.strip() for x in source.get(option).splitlines() if x]
            self.recipe.patch(patches,
                              command_options=source.get(self.resolve_stage(
                                  'patch-options', stage=stage), None),
                              command_binary=source.get(self.resolve_stage(
                                  'patch-binary', stage=stage), None),
                              cwd=source[cwdkey])

    def render_template_source(self, source, cwdkey='source-directory', stage=None):
        template_sources_option = self.resolve_stage('template-sources', stage=stage)
        template_destinations_option = self.resolve_stage('template-destinations', stage=stage)
        if template_sources_option in source:
            template_sources = [x.strip() for x in source.get(
                                template_sources_option).splitlines() if x]
            template_destinations = [x.strip() for x in source.get(
                                     template_destinations_option).splitlines() if x]
            template_context = [x.strip().split('=') for x in source.get(
                                self.resolve_stage('template-context', stage=stage)).splitlines()
                                if x]
            template_destination = source.get(template_destination_option, source[cwdkey])
            for tempate_source, template_destination in zip(template_sources, template_destinations):
                if not os.path.isabs(template_source):
                    template_source = os.path.join(source[cwdkey], template_source)
                if not os.path.isabs(template_destination):
                    template_destination = os.path.join(source[cwdkey], template_destination)
                self.recipe.render_template(template_source,
                                            template_destination,
                                            **template_context)

    def process_source(self, source):
        raise NotImplementedError


class BaseSourceRecipe(BaseGroupRecipe):
    """
    An abstract recipe to manage a source.
    """

    def initialize(self):
        super(BaseSourceRecipe, self).initialize()
        self.sources = defaultdict(list)
