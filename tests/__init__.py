
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


#class TestDockerEngineMethods(unittest.TestCase):
#    def test_layout(self):
#        dm = DockerEngine()
#        root = tempfile.mkdtemp()
#        image = "{}:latest".format(dm.get_random_name().lower())
#        container = dm.get_random_name().lower()
#        dm.import_path(root, image)
#        dm.create_container(container, image, command="/bin/freeze")
#        dm.load_layout(container, os.path.dirname(__file__))
#        dm.save_layout(container, "/", root)
#        self.assertTrue(os.path.isfile(os.path.join(root, os.path.basename(__file__))))
#        dm.remove_container(container)
#        dm.remove_image(image)
#        shutil.rmtree(root)


from doctest import DocTestSuite, OutputChecker
from importlib import import_module
import os
import re
import shutil
from unittest import TestSuite

from zc.buildout.testing import buildoutSetUp, buildoutTearDown, install_develop


def setUp(test):
    home = os.environ.get('HOME', None)
    buildoutSetUp(test)
    os.environ['HOME'] = home
    class buildout_test(object):
        def __init__(self, config):
            self.config = config

        def reset(self):
            test.globs['write'](test.globs['sample_buildout'], 'buildout.cfg',
                os.linesep.join(('[buildout]', 'offline=true', 'parts =')))
            test.globs['system'](test.globs['buildout'])

        def __enter__(self):
            self.reset()
            test.globs['write'](test.globs['sample_buildout'], 'buildout.cfg', self.config)
            return self

        def run(self, *args):
            return test.globs['system'](' '.join([test.globs['buildout']] + list(args)))

        def __exit__(self, type, value, traceback):
            self.reset()
    test.globs['server_path'] = server_path = test.globs['tmpdir']('server')
    shutil.copytree(os.path.join(os.path.dirname(__file__), 'data'),
        os.path.join(server_path, 'data'))
    test.globs['server_url'] = test.globs['start_server'](server_path)
    test.globs['buildout_test'] = buildout_test
    install_develop('dockeroo', test)

class RecipeOutputChecker(OutputChecker):
    def __init__(self, patterns):
        self.patterns = patterns

    def check_output(self, want, got, optionflags):
        if got == want:
            return True

        for pattern, repl in self.patterns:
            want = re.sub(pattern, repl, want)
            got = re.sub(pattern, repl, got)

        return OutputChecker.check_output(self, want, got, optionflags)

    def output_difference(self, example, got, optionflags):
        want = example.want

        if not want.strip():
            return OutputChecker.output_difference(
                self, example, got, optionflags)

        orig = want

        for pattern, repl in self.patterns:
            want = re.sub(pattern, repl, want)
            got = re.sub(pattern, repl, got)

        example.want = want
        result = OutputChecker.output_difference(
            self, example, got, optionflags)
        example.want = orig

        return result

PATTERNS = (
    (re.compile(r'^zip_safe flag not set; analyzing archive contents...\n', flags=re.MULTILINE), ''),
    (re.compile(r'^[\w\._]+: module MAY be using inspect.stack\n', flags=re.MULTILINE), ''),
    (re.compile(r'^[\w\._]+: module references __(file|path)__\n', flags=re.MULTILINE), ''),
    (re.compile(r'^warning: no files found matching .*\n', flags=re.MULTILINE), ''),
    (re.compile(r'^Not found: [^\n]+/(\w|\.)+/\r?\n', flags=re.MULTILINE), ''),
    (re.compile(r'^Getting distribution for \'\w+\'.\n', flags=re.MULTILINE), ''),
    (re.compile(r'^Got \w+ [\d\.]*\d.\n', flags=re.MULTILINE), ''),

    (re.compile(r'Downloading .*'), 'Downloading <URL>'),

    (re.compile(r'\w+ version [\d\.]*\d'), '<PACKAGE> version <VERSION>'),
    (re.compile(r'''(?<=["'=])\w+://[^"']+'''), '<URL>'),
    (re.compile(r'''(?<=["'=])/[^"']+'''), '<PATH>'),
    (re.compile(r'''(?<=[\s])/[^\s]+'''), '<PATH>'),
)

MODULES = [
    'dockeroo',
    'dockeroo.docker',
#    'dockeroo.docker.build',
#    'dockeroo.docker.copy',
#    'dockeroo.docker.gentoo_bootstrap',
#    'dockeroo.docker.gentoo_build',
#    'dockeroo.docker.gentoo_diskimage',
#    'dockeroo.docker.network',
#    'dockeroo.docker.pull',
#    'dockeroo.docker.push',
#    'dockeroo.docker.run',
#    'dockeroo.docker.volume',
    'dockeroo.setup.download',
    'dockeroo.setup.cmmi',
    'dockeroo.setup.egg',
    'dockeroo.setup.shell_script',
    'dockeroo.setup.template',
#    'dockeroo.utils',
]

tests = TestSuite(
    map(lambda module: DocTestSuite(import_module(module),
        setUp=setUp,
        tearDown=buildoutTearDown,
        checker=RecipeOutputChecker(PATTERNS)),
        MODULES))
