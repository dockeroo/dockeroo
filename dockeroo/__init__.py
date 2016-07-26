from builtins import range
from builtins import object

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
import errno
from importlib import import_module
from itertools import chain
import logging
import os
from platform import uname
import random
from select import select
import shlex
import shutil
import string
import subprocess
import sys
from future.moves.urllib.parse import parse_qs

from zc.buildout import UserError
from zc.buildout.download import Download

from dockeroo import filters
from dockeroo.filters import scm as filters_scm
from dockeroo.filters import RecipeFilter
from dockeroo.utils import ExternalProcessError
from dockeroo.utils import OptionRepository, reify
from dockeroo.utils import resolve_loglevel, resolve_verbosity
from dockeroo.utils import string_as_bool, uniq


FILTERS = []

class RecipeFilterset(object):
    _filters = defaultdict(list)

    def __init__(self, recipe):
        self.recipe = recipe
        for flt in FILTERS:
            self.add(flt)

    def add(self, cls):
        self._filters[cls.filter_category].append(cls(self.recipe))

    def __call__(self, filter_category, args=None, kwargs=None, continue_on_success=False):
        args = args or []
        kwargs = kwargs or {}
        rets = []
        for fltr in self._filters[filter_category]:
            ret = fltr(*args, **kwargs)
            if ret is not None:
                if not continue_on_success:
                    return ret
                else:
                    rets.append(ret)
        return rets or None

    @classmethod
    def preload_filters(cls, base_module):
        import inspect
        from warnings import warn

        for module_name in \
            [os.path.splitext(entry)[0] \
             for entry in [entry for entry in os.listdir(os.path.dirname(base_module.__file__)) \
             if entry.endswith('.py') and not entry.startswith('__')]]:

            try:
                module = import_module("{}.{}".format(
                    base_module.__name__, module_name))
            except Exception as e:
                warn('''Unable to import module "{}": {}'''.format(module_name, e))
            else:
                for fltr in [entry for entry in [getattr(module, entry) for entry in dir(module)] \
                             if inspect.isclass(entry) and
                             issubclass(entry, RecipeFilter) and
                             hasattr(entry, 'filter_category') and entry.filter_category]:

                    FILTERS.append(fltr)

RecipeFilterset.preload_filters(filters)
RecipeFilterset.preload_filters(filters_scm)


class BaseRecipe(object):
    loggers = [__name__, 'zc.buildout']

    def __init__(self, buildout, name, options):
        self.logger = logging.getLogger(__name__)
        self.cleanup_paths = set()
        self.options = OptionRepository(options)
        self.buildout = buildout
        self.part_name = name
        self.options.setdefault('name', name)
        self.filterset = RecipeFilterset(self)
        self.log_handler = logging.StreamHandler(sys.stdout)
        self.initialize()

    @classmethod
    def _uninstall(cls, name, options):
        return cls({}, name, options).uninstall()

    def setup_logging(self):
        self._save_logging = {}
        for logger in [logging.getLogger(x) for x in self.loggers]:
            self.save_logger(logger)
            logging._acquireLock()
            logger.handlers = [self.log_handler]
            logging._releaseLock()
            logger.propagate = False

    def restore_logging(self):
        for logger in [logging.getLogger(x) for x in self.loggers]:
            self.restore_logger(logger)

    def save_logger(self, logger):
        logging._acquireLock()
        self._save_logging['{}_handlers'.format(
            logger.name)] = list(logger.handlers)
        logging._releaseLock()
        self._save_logging['{}_propagate'.format(
            logger.name)] = logger.propagate

    def restore_logger(self, logger):
        logging._acquireLock()
        logger.handlers = self._save_logging.pop(
            '{}_handlers'.format(logger.name))
        logging._releaseLock()
        logger.propagate = self._save_logging.pop(
            '{}_propagate'.format(logger.name))

    def set_logging(self, fmt, level, verbosity=0):
        self.log_handler.setFormatter(logging.Formatter(fmt))
        for logger in [logging.getLogger(x) for x in self.loggers]:
            logger.setLevel(level - verbosity)

    @property
    def name(self):
        return self.options.get('name', None)

    @name.setter
    def name(self, value):
        self.options.set('name', value)

    @property
    @reify
    def offline(self):
        return string_as_bool(self.buildout['buildout'].get('offline', False))

    @property
    @reify
    def newest(self):
        return string_as_bool(self.buildout['buildout'].get('newest', False))

    @property
    @reify
    def download_hashing(self):
        return string_as_bool(self.buildout['buildout'].get('hash-name', True))

    @property
    @reify
    def download_cache(self):
        return self.buildout['buildout'].get('download-cache', None)

    @property
    @reify
    def download_manager(self):
        return Download(self.buildout['buildout'],
                        hash_name=self.options.get(
                            'download-hashing',
                            default=self.buildout.get('download-hashing', True)),
                        cache=self.download_cache,
                        logger=self.logger)

    @property
    @reify
    def default_executable(self):
        return self.buildout['buildout'].get('executable', sys.executable)

    @property
    @reify
    def default_location(self):
        return os.path.join(self.buildout['buildout']['parts-directory'], self.name)

    @property
    @reify
    def default_working_directory(self):
        return os.path.join(
            self.buildout['buildout']['parts-directory'],
            "{}.workdir{}".format(
                self.name,
                ''.join(random.choice(string.ascii_letters + string.digits) \
                    for _ in range(8))))

    @property
    @reify
    def default_log_format(self):
        return self.buildout['buildout']['log-format'] or "%(name)s: %(message)s"

    @property
    @reify
    def default_log_level(self):
        return resolve_loglevel(self.buildout['buildout']['log-level'])

    @property
    @reify
    def default_verbosity(self):
        return resolve_verbosity(self.buildout['buildout']['verbosity'])

    def initialize(self):
        self.set_logging(self.default_log_format,
                         self.default_log_level)

        if 'install-script' in self.options[None]:
            self._install_script = self.options.get('install-script')
        elif 'script' in self.options[None]:
            self._install_script = self.options.get('script')
        elif hasattr(self, 'install_script'):
            self._install_script = self.install_script
        else:
            raise UserError(
                '''You must provide a "script" or "install-script" field.''')

        if 'update-script' in self.options[None]:
            self._update_script = self.options.get('update-script')
        elif 'script' in self.options[None]:
            self._update_script = self.options.get('script')
        elif hasattr(self, 'update_script'):
            self._update_script = self.update_script
        if self.update_script is not None:
            self.update = self.update_wrapper

        if 'uninstall-script' in self.options[None]:
            self._uninstall_script = self.options.get('uninstall-script')
        elif 'script' in self.options[None]:
            self._uninstall_script = self.options.get('script')
        elif hasattr(self, 'uininstall_script'):
            self._uininstall_script = self.uininstall_script
        if self.uninstall_script is not None:
            self.uninstall = self.uninstall_wrapper

    def download(self, url, params=None, force=False):
        return self.filterset('download', [url.strip()], {'params': params or {}, 'force': force})

    def extract_archive(self, src, dst, params=None):
        return self.filterset('extract.archive', [src.strip(), dst], {'params': params or {}})

    def extract_scm(self, repo_type, src, dst, params=None):
        return self.filterset('extract.scm',
                              [repo_type, src.strip(), dst],
                              {'params': params or {}})

    @property
    @reify
    def locations(self):
        return uniq([_f for _f in [self.default_location] +
                     getattr(self, 'extra_locations', []) if _f])

    @property
    @reify
    def working_directories(self):
        return uniq([self.default_working_directory])

    def install_wrapper(self):
        self.setup_logging()
        exc = None
        try:
            for location in self.locations:
                if os.path.exists(location):
                    self.cleanup_paths.add(location)
                    raise shutil.Error(
                        '''Directory "{}" already exists'''.format(location))
            for working_directory in self.working_directories:
                self.mkdir(working_directory)
                self.cleanup_paths.add(working_directory)
            if callable(self._install_script):
                self._install_script()
            else:
                exec(self._install_script)
        except Exception as e:
            exc = e
            self.restore_logging()
            raise
        finally:
            if exc is not None and string_as_bool(self.options.get('keep-on-error', False)):
                for f in self.cleanup_paths:
                    self.logger.info('Left path "%s" as requested', f)
            else:
                for f in self.cleanup_paths:
                    self.logger.debug('Cleaning up "%s"', f)
                    self.rm(f)
        specs = self.options.get('specs', default=None)
        if specs is not None:
            self.check_specs(specs)
        self.restore_logging()
        return self.locations
    install = install_wrapper

    def update_wrapper(self):
        self.setup_logging()
        exc = None
        try:
            for working_directory in self.working_directories:
                self.mkdir(working_directory)
                self.cleanup_paths.add(working_directory)
            if callable(self._update_script):
                self._update_script()
            else:
                exec(self._update_script)
        except Exception as e:
            exc = e
            self.restore_logging()
            raise
        finally:
            if exc is not None and string_as_bool(self.options.get('keep-on-error', False)):
                for f in self.cleanup_paths:
                    self.logger.info('Left path "%s" as requested', f)
            else:
                for f in self.cleanup_paths:
                    self.logger.debug('Cleaning up "%s"', f)
                    self.rm(f)
        specs = self.options.get('specs', default=None)
        if specs is not None:
            self.check_specs(specs)
        self.restore_logging()
        return self.locations

    def uninstall_wrapper(self):
        self.setup_logging()
        try:
            if callable(self._uninstall_script):
                self._uninstall_script()
            else:
                exec(self._uninstall_script)
        except Exception:
            self.restore_logging()
            raise
        self.restore_logging()

    def _default_install_script(self):
        pass

    def _default_update_script(self):
        pass

    def check_specs(self, specs):
        pass

    def pipe_command(self, command_list, *args, **kwargs):
        subprocess_list = []
        previous = None
        kwargs['stdout'] = subprocess.PIPE
        run_list = []
        for command in command_list:
            if previous is not None:
                kwargs['stdin'] = previous.stdout
            p = subprocess.Popen(command, *args, **kwargs)
            if previous is not None:
                previous.stdout.close()
            subprocess_list.append((p, command))
            run_list.append(' '.join(command))
            previous = p
        self.logger.info('Running: "%s"', ' | '.join(run_list))
        subprocess_list.reverse()
        [q[0].wait() for q in subprocess_list]
        for q in subprocess_list:
            if q[0].returncode != 0:
                raise UserError(
                    '''Failed while running command "{}"'''.format(q[1]))

    def fail_if_path_exists(self, path):
        if os.path.lexists(path):
            raise UserError(
                '''Path "{}" exists, cannot continue'''.format(path))

    def copy(self, origin, destination):
        if os.path.isfile(origin):
            shutil.copy(origin, destination)
        else:
            self.copy_tree(origin, destination)
        return destination

    def copy_tree(self, origin, destination, ignore=None):
        if os.path.exists(destination):
            raise shutil.Error(
                '''Destination already exists: "{}"'''.format(destination))
        self.logger.debug('Copying "%s" to "%s"', origin, destination)
        try:
            shutil.copytree(origin, destination,
                            ignore=shutil.ignore_patterns(*ignore or []))
        except (shutil.Error, OSError) as error:
            try:
                shutil.rmtree(destination, ignore_errors=True)
            except (shutil.Error, OSError) as strerror:
                self.logger.error('Error occurred when cleaning after error: "%s"', strerror)
            raise error

    def mkdir(self, *paths):
        for path in paths:
            try:
                os.makedirs(path)
            except OSError as e:
                if e.errno == errno.EEXIST and os.path.isdir(path):
                    pass
                else:
                    raise

    def rm(self, *paths):
        for path in paths:
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.exists(path):
                os.remove(path)

    def patch(self, patch_spec, prefix=None, command_options=None, command_binary=None, cwd=None):
        params = {
            'command-options': shlex.split(command_options) if command_options is not None else [],
            'command-binary': command_binary.strip() if command_binary is not None else 'patch',
        }
        if cwd is not None:
            params['cwd'] = cwd.strip()
        for patch in patch_spec.splitlines():
            patch = patch.strip()
            if not patch:
                continue
            if '#' in patch:
                patch, params_string = patch.split('#', 1)
                params.update(parse_qs(params_string))
            if prefix is not None:
                patch = os.path.join(prefix, patch)
            self.logger.info('Applying patch: "%s"', patch)
            self.filterset('patch', [patch], {'params': params})

    def call(self, *args, **kwargs):
        kwargs.update(close_fds=True, stdout=subprocess.PIPE,
                      stderr=subprocess.PIPE)
        ignore_errnos = kwargs.pop('ignore_errnos', [])
        stdout_log_level = kwargs.pop(
            'stdout_log_level', self.default_log_level)
        stderr_log_level = kwargs.pop('stderr_log_level', logging.ERROR)
        popen = subprocess.Popen(args, **kwargs)
        log_level = {popen.stdout: stdout_log_level,
                     popen.stderr: stderr_log_level}

        def check_io():
            for io in select([popen.stdout, popen.stderr], [], [], 1000)[0]:
                line = io.readline().strip()
                if line:
                    self.logger.log(log_level[io], '%s', line)
        while popen.poll() is None:
            check_io()
        check_io()
        returncode = popen.wait()
        if returncode != 0 and returncode not in ignore_errnos:
            raise subprocess.CalledProcessError(returncode, ' '.join(args))
        return returncode

    def calls(self, cmd, **kwargs):
        """Subprocesser caller which allows to pass arguments as string"""
        return self.call(shlex.split(cmd), **kwargs)

    @classmethod
    def guess_main_directory(cls, path):
        if len(os.listdir(path)) == 1:
            child = os.listdir(path)[0]
            if os.path.isdir(os.path.join(path, child)):
                return os.path.join(path, child)
        return path


class BaseSubRecipe(object):

    def __init__(self, recipe, group):
        self.recipe = recipe
        self.group = group
        self.logger = recipe.logger
        self.options = recipe.options[group]

    @property
    def name(self):
        return self.options.get('name', None)

    @name.setter
    def name(self, value):
        self.options.set('name', value)

    @property
    @reify
    def working_directory(self):
        return self.options.get('working-directory',
                                self.recipe.default_working_directory)

    @property
    @reify
    def executable(self):
        if self.group is None:
            default = self.recipe.default_executable
        else:
            default = self.recipe.options[None].location
        return self.options.get('executable', default)

    @property
    @reify
    def environment_config(self):
        env = {}
        for line in self.options.get('environment', default='').splitlines():
            line = line.strip()
            if not line:
                continue
            if not '=' in line:
                raise UserError(
                    '''Line "{}" in environment is incorrect'''.format(line))
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            if key in env:
                raise UserError('''Key "{}" is repeated'''.format(key))
            env[key] = value
        return env

    @property
    @reify
    def environment(self):
        config = self.environment_config.copy()
        env = {}
        for k, v in os.environ.items():
            change = config.pop(k, None)
            if change is not None:
                env[k] = change % os.environ
                self.logger.info(
                    '''Environment "{}" set to "{}"'''.format(k, env[k]))
            else:
                env[k] = v
        for k, v in config.items():
            self.logger.info(
                '''Environment "{}" added with "{}"'''.format(k, v))
            env[k] = v
        return env

    @property
    @reify
    def location(self):
        if self.group is None:
            default = self.recipe.default_location
        else:
            default = self.recipe.options[None].location
        return self.options.get('location', default)

    @property
    @reify
    def log_format(self):
        return self.options.get('log-format',
                                self.recipe.default_log_format)

    @property
    @reify
    def log_level(self):
        return self.options.get('log-level',
                                self.recipe.default_log_level)

    def initialize(self):
        self.recipe.set_logging(self.log_format,
                                self.log_level)


class BaseGroupRecipe(BaseRecipe):
    subrecipe_class = NotImplemented

    def __init__(self, buildout, name, options):
        super(BaseGroupRecipe, self).__init__(buildout, name, options)
        if self.subrecipe_class is NotImplemented:
            raise ValueError("subrecipe_class has not been set")
        for group in self.options:
            self.subrecipes[group] = self.subrecipe_class(self, group) # pylint: disable=not-callable
            self.subrecipes[group].initialize()

    @property
    @reify
    def locations(self):
        return uniq([_f for _f in
                     chain(*[[x.location] + getattr(x, 'extra_locations', [])
                             for x in self.subrecipes.values()]) if _f])

    @property
    @reify
    def working_directories(self):
        return uniq([x.working_directory for x in self.subrecipes.values()])

    def initialize(self):
        self.update = self.update_wrapper
        self.subrecipes = dict()

    def script(self, name, *args, **kwargs):
        for group in self.subrecipes:
            attr = getattr(self.subrecipes[group], name)
            if callable(attr):
                attr(*args, **kwargs)
            else:
                exec(attr)

    def install_script(self):
        return self.script('install')

    def update_script(self):
        return self.script('update')

    def uninstall_script(self):
        return self.script('uninstall')
