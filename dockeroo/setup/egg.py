
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


import logging
import os
import re
import string
import sys
from copy import copy
from tempfile import mkdtemp, mkstemp

from builtins import str # pylint: disable=redefined-builtin
from setuptools.command.setopt import edit_config as setuptools_edit_config
from pkg_resources import WorkingSet, Environment, Requirement, DEVELOP_DIST
from pkg_resources import SOURCE_DIST, EGG_DIST, BINARY_DIST
from zc.buildout import UserError
from zc.buildout.easy_install import default_index_url, _get_index as get_index
from zc.buildout.easy_install import runsetup_template as setup_template
from zc.buildout.easy_install import setuptools_loc as setuptools_location
from zc.buildout.easy_install import buildout_and_setuptools_path

from dockeroo.setup.download import BaseDownloadSubRecipe, SetupDownloadRecipe
from dockeroo.utils import reify, string_as_bool


SIGNATURE_MARKER = 'zdockeroo'

BUILD_EXT_OPTIONS = frozenset((
    'compiler',
    'debug',
    'define',
    'force',
    'include-dirs',
    'libraries',
    'library-dirs',
    'link-objects',
    'plat-name',
    'rpath',
    'swig',
    'swig-cpp',
    'swig-opts',
    'undef',
    'user',
    #'build-lib',
    #'build-temp',
    #'inplace',
))


class SetupEggSubRecipe(BaseDownloadSubRecipe):

    @property
    @reify
    def index_url(self):
        return self.options.get(
            'index',
            self.recipe.buildout['buildout'].get('index', default_index_url))

    @property
    @reify
    def find_links_urls(self):
        return self.options.get(
            'find-links',
            self.recipe.buildout['buildout'].get('find-links', '')).split()

    @property
    @reify
    def source_key_processors(self):
        return {
            'egg': lambda x: [('egg', x.strip())],
            'eggs': lambda x: [('egg', y.strip()) for y in x.splitlines()],
        }

    @property
    @reify
    def source_option_processors(self):
        ret = super(SetupEggSubRecipe, self).source_option_processors.copy()
        ret.update({
            'build': string_as_bool,
            'build-dependencies': string_as_bool,
            'extra-paths': lambda x: [x.strip() for x in x.splitlines()],
            'egg-path': lambda x: [x.strip() for x in x.splitlines()],
        })
        return ret

    @property
    @reify
    def allowed_options(self):
        ret = copy(super(SetupEggSubRecipe, self).allowed_options)
        ret.extend([
            'egg-name',
            'find-egg',
            'path',
            'signature',
            'url',
        ])
        for stage in ['after-build']:
            ret.extend([
                self.resolve_stage('patch', stage=stage),
                self.resolve_stage('patch-options', stage=stage),
                self.resolve_stage('patch-binary', stage=stage),
            ])
        return ret

    def initialize(self):
        super(SetupEggSubRecipe, self).initialize()
        if self.recipe.options.get_as_bool('split-working-set', False):
            self.working_set = WorkingSet([])
        else:
            self.working_set = self.recipe.working_set
        self.index = get_index(self.index_url, self.find_links_urls)

    def default_eggs_directory(self, develop=False):
        if develop and 'develop-eggs-directory' in self.recipe.buildout['buildout']:
            return self.recipe.buildout['buildout']['develop-eggs-directory']
        elif 'eggs-directory' in self.recipe.buildout['buildout']:
            return self.recipe.buildout['buildout']['eggs-directory']
        else:
            return os.path.join(os.path.dirname(sys.argv[0]), '..', 'eggs')

    def populate_source(self, source, dependency=False):
        super(SetupEggSubRecipe, self).populate_source(
            source, load_options=not dependency)
        if 'egg' not in source:
            source['egg'] = self.name
        source['requirement'] = Requirement.parse(source['egg'])
        source['egg'] = str(source['requirement'])
        source['find-requirement'] = Requirement.parse(source['find-egg']) \
            if 'find-egg' in source else source['requirement']
        source['find-egg'] = str(source['find-requirement'])
        source.setdefault('build', True)
        egg_directories = []
        if 'develop-eggs-directory' in self.recipe.buildout['buildout']:
            egg_directories.append(self.recipe.buildout['buildout']['develop-eggs-directory'])
        if 'eggs-directory' in self.recipe.buildout['buildout']:
            egg_directories.append(self.recipe.buildout['buildout']['eggs-directory'])
        source.setdefault('egg-path',
                          [source['location']] if 'location' in source else [] +
                          source.get('extra-paths', []) + egg_directories +
                          buildout_and_setuptools_path)
        source.setdefault('location',
                          self.default_eggs_directory(develop=source.get('develop', False)))
        source['egg-environment'] = Environment(source['egg-path'])
        source['build-options'] = {}
        if not dependency:
            for src_key, dst_key in [(key, re.sub('-', '_', key)) for key in
                                     [option for option in self.options
                                      if option in BUILD_EXT_OPTIONS]]:
                source['build-options'][dst_key] = self.options[src_key]
        source.setdefault('signature', self.resolve_signature(source))

    def process_source(self, source):
        if self.working_set.find(source['requirement']) is not None:
            return
        if source['build']:
            self.build_source(source)
        self.patch_source(source, cwdkey='build-directory',
                          stage='after-build')
        self.install_source(source)

    def acquire_source(self, source, destkey='working-directory'):
        candidates = self.requirement_match_list(source['egg-environment'], source['requirement'],
                                                 strip_signature=source['signature'])
        if not candidates or self.recipe.newest:
            if 'url' not in source:
                if self.recipe.offline:
                    raise UserError(
                        '''Couldn't download index "{}" in offline mode.'''.format(self.index))
                self.index.find_packages(source['find-requirement'])
                distributions = self.requirement_match_list(
                    self.index, source['find-requirement'],
                    requirement_type=self.requirement_type(source))
                if not distributions:
                    raise UserError('''No distributions available for requirement "{}".'''.format(
                        source['find-egg']))
                if not candidates or distributions[0].parsed_version > candidates[0].parsed_version:
                    source['url'] = distributions[0].location
                    source['egg-name'] = distributions[0].egg_name()
                else:
                    source['source-directory'] = candidates[0].location
                    source['build'] = False
                    source['egg-name'] = candidates[0].egg_name()
            if 'source-directory' not in source:
                self.logger.info("Getting distribution for '{}'.".format(
                    source['requirement'].project_name))
                super(SetupEggSubRecipe, self).acquire_source(source, destkey=destkey)
        else:
            source['source-directory'] = candidates[0].location
            source['build'] = False
            source['egg-name'] = candidates[0].egg_name()
        if source.get('build-dependencies', True):
            sourceenv = Environment([source['source-directory']])
            for key in sourceenv:
                for dist in sourceenv[key]:
                    for dependency_requirement in dist.requires():
                        dependency_source = {'egg': str(
                            dependency_requirement), 'parent-egg': str(source['egg'])}
                        self.sources.insert(self.sources.index(
                            source), dependency_source)
                        self.populate_source(
                            dependency_source, dependency=True)
                        self.prepare_source(dependency_source)

    def build_source(self, source):
        self.logger.info('''Building: {}'''.format(source['egg-name']))
        undo = []
        setup_py = os.path.join(source['source-directory'], 'setup.py')
        try:
            setup_cfg = os.path.join(source['source-directory'], 'setup.cfg')
            if os.path.exists(setup_cfg):
                os.rename(setup_cfg, setup_cfg + '-develop-aside')

                def restore_old_setup():
                    if os.path.exists(setup_cfg):
                        os.remove(setup_cfg)
                    os.rename(setup_cfg + '-develop-aside', setup_cfg)
                undo.append(restore_old_setup)
            else:
                open(setup_cfg, 'w').close()
                undo.append(lambda: os.remove(setup_cfg))
            updates = {}
            if source['build-options']:
                updates['build_ext'] = source['build-options']
            if source['signature']:
                updates['egg_info'] = {
                    'tag_build': "_{}".format(source['signature']),
                }
            setuptools_edit_config(setup_cfg, updates)

            setup_cmd_fd, setup_cmd = mkstemp(dir=source['source-directory'])
            setup_cmd_fh = os.fdopen(setup_cmd_fd, 'w')
            undo.append(lambda: os.remove(setup_cmd))
            undo.append(setup_cmd_fh.close)

            setup_cmd_fh.write((setup_template % dict(
                setuptools=setuptools_location,
                setupdir=source['source-directory'],
                setup=setup_py,
                __file__=setup_py,
            )).encode())
            setup_cmd_fh.flush()

            build_directory = mkdtemp('build',
                                      dir=source['source-directory'])

            action_args = []
            if source.get('develop', False) is True:
                action = 'develop'
                action_args.append('-Z')
            else:
                action = 'easy_install'
                action_args.append(source['source-directory'])

            args = [source['executable'], setup_cmd, action, '-mxNd',
                    build_directory]
            if self.log_level < logging.INFO:
                args += ['-v']
            elif self.log_level > logging.INFO:
                args += ['-q']
            args += action_args

            self.logger.debug('''Running: {}'''.format(' '.join(args)))
            self.recipe.call(*args, stdout_log_level=logging.DEBUG)
            source['build-directory'] = build_directory
        finally:
            for obj in reversed(undo):
                obj()

    def install_source(self, source, destkey='location'):
        if 'build-directory' not in source:
            return
        env = Environment([source['build-directory']])
        self.recipe.mkdir(source[destkey])
        for dists in [env[x] for x in env]:
            for src_dist in dists:
                dst_dist = src_dist.clone(
                    location=os.path.join(source[destkey],
                                          "{}.{}".format(src_dist.egg_name(), {
                                              EGG_DIST: 'egg',
                                              DEVELOP_DIST: 'egg-link',
                                          }[src_dist.precedence])))
                {
                    EGG_DIST: lambda src, dst:
                              self.recipe.copy(src, dst)
                              if os.path.isdir(src) else
                              self.recipe.extract_archive(src, dst),
                    DEVELOP_DIST: os.rename,
                }[src_dist.precedence](src_dist.location, dst_dist.location)
                # redo_pyc(newloc)
                self.working_set.add_entry(dst_dist.location)
                self.logger.info('''Got {}.'''.format(
                    str(dst_dist.egg_name())))

    @classmethod
    def requirement_match_list(cls, index, requirement, requirement_type=None,
                               prefer_final=True, strip_signature=''):
        def mangle_candidate(dist):
            if strip_signature:
                dist = dist.clone(version=re.sub(
                    r'_{}$'.format(strip_signature), '', dist.version))
            return dist
        candidates = [candidate for candidate in index[requirement.project_name]
                      if mangle_candidate(candidate) in requirement]
        if not candidates:
            return []
        if requirement_type is not None:
            candidates = [candidate for candidate in candidates
                          if candidate.precedence == requirement_type]
        if prefer_final:
            final_candidates = [candidate for candidate in candidates
                                if not candidate.parsed_version.is_prerelease]
            if final_candidates:
                candidates = final_candidates
        best = []
        bestv = None
        for candidate in candidates:
            candidatev = candidate.parsed_version
            if not bestv or candidatev > bestv:
                best = [candidate]
                bestv = candidatev
            elif candidatev == bestv:
                best.append(candidate)
        best.sort()
        return best

    @classmethod
    def requirement_type(cls, source):
        egg_type = source.get('egg-type', None)
        try:
            return {
                'source': SOURCE_DIST,
                'binary': BINARY_DIST,
                None: None,
            }[egg_type]
        except KeyError:
            return None

    @classmethod
    def resolve_signature(cls, source):
        struct = []
        for key, value in source['build-options'].items():
            struct.append((key, value))
        for key in ('patches', 'patch-options', 'patch-binary'):
            if key in source:
                struct.append(source[key])
        struct = tuple(struct) # pylint: disable=redefined-variable-type
        if not struct:
            return None
        base = string.digits + string.letters
        base_length = len(base)
        ret = ''
        struct_hash = abs(hash(struct))
        while struct_hash > 0:
            ret = base[struct_hash % base_length] + ret
            struct_hash /= base_length
        return "{}_{}".format(SIGNATURE_MARKER, ret)


class SetupEggRecipe(SetupDownloadRecipe):
    """
    A recipe to build an egg package.

    Example:

        >>> with buildout_test('''
        ... [buildout]
        ... index = %(server)sdata/index.html
        ... find-links =
        ...     %(server)sdata/dummy/index.html
        ...     https://pypi.python.org/simple/future/
        ...     https://pypi.python.org/simple/setuptools/
        ...     https://pypi.python.org/simple/shellescape/
        ...     https://pypi.python.org/simple/tzlocal/
        ... parts = part
        ...
        ... [part]
        ... recipe = dockeroo:setup.egg
        ... egg = dummy
        ... ''' % dict(server=server_url)) as b:
        ...     print_(b.run(), end='')
        Installing part.
        dockeroo: Getting distribution for 'dummy'.
        dockeroo: Downloading <URL>
        dockeroo: Building: dummy-0.1-py2.7
        dockeroo: Got dummy-0.1-py2.7.
    """

    subrecipe_class = SetupEggSubRecipe

    def initialize(self):
        super(SetupEggRecipe, self).initialize()
        self.working_set = WorkingSet([])

    default_location = None
