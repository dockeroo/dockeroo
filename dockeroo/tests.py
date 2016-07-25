
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
import shutil
import tempfile
import unittest

from dockeroo import DockerEngine


class TestDockerEngineMethods(unittest.TestCase):
    def test_client_environment(self):
        dm = DockerEngine()
        self.assertIn('DOCKER_TLS_VERIFY', dm.client_environment)
        self.assertIn('DOCKER_HOST', dm.client_environment)
        self.assertIn('DOCKER_CERT_PATH', dm.client_environment)
        self.assertIn('DOCKER_MACHINE_NAME', dm.client_environment)
        self.assertEqual(dm.client_environment['DOCKER_MACHINE_NAME'], dm.machine.name)

    def test_client_version(self):
        dm = DockerEngine()
        self.assertRegexpMatches(dm.client_version, r'^\d+.\d+.\d+$')

    def test_machine_platform(self):
        dm = DockerEngine()
        self.assertIn(dm.machine.platform, (
            'arm', 'armv4', 'armv4t', 'armv5te', 'armv6j', 'armv7a',
            'hppa', 'hppa1.1', 'hppa2.0', 'hppa64',
            'i386', 'i486', 'i586', 'i686',
            'ia64',
            'm68k',
            'mips', 'mips64',
            'powerpc', 'powerpc64',
            's390',
            'sh', 'sh4', 'sh64',
            'sparc', 'sparc64',
            'x86_64'))

    def test_machine_url(self):
        dm = DockerEngine()
        self.assertRegexpMatches(dm.machine.url, '^tcp://')

    def test_import_path(self):
        dm = DockerEngine()
        root = tempfile.mkdtemp()
        image = "{}:latest".format(dm.get_random_name().lower())
        dm.import_path(root, image)
        self.assertTrue(dm.images(name=image))
        dm.remove_image(image)
        shutil.rmtree(root)

    def test_layout(self):
        dm = DockerEngine()
        root = tempfile.mkdtemp()
        image = "{}:latest".format(dm.get_random_name().lower())
        container = dm.get_random_name().lower()
        dm.import_path(root, image)
        dm.create_container(container, image, command="/bin/freeze")
        dm.load_layout(container, os.path.dirname(__file__))
        dm.save_layout(container, "/", root)
        self.assertTrue(os.path.isfile(os.path.join(root, os.path.basename(__file__))))
        dm.remove_container(container)
        dm.remove_image(image)
        shutil.rmtree(root)
