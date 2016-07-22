
from dockeroo import DockerMachine

import os
import shutil
import tempfile
import unittest


class TestDockerMachineMethods(unittest.TestCase):
    def test_client_environment(self):
        dm = DockerMachine()
        self.assertIn('DOCKER_TLS_VERIFY', dm.client_environment)
        self.assertIn('DOCKER_HOST', dm.client_environment)
        self.assertIn('DOCKER_CERT_PATH', dm.client_environment)
        self.assertIn('DOCKER_MACHINE_NAME', dm.client_environment)
        self.assertEqual(dm.client_environment['DOCKER_MACHINE_NAME'], dm.machine_name)

    def test_client_version(self):
        dm = DockerMachine()
        self.assertRegexpMatches(dm.client_version, r'^\d+.\d+.\d+$')

    def test_machine_platform(self):
        dm = DockerMachine()
        self.assertIn(dm.machine_platform, (
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
        dm = DockerMachine()
        self.assertRegexpMatches(dm.machine_url, '^tcp://')

    def test_import_path(self):
        dm = DockerMachine()
        root = tempfile.mkdtemp()
        image = "{}:latest".format(dm.get_random_name().lower())
        dm.import_path(root, image)
        self.assertTrue(dm.images(name=image))
        dm.remove_image(image)
        shutil.rmtree(root)

    def test_layout(self):
        dm = DockerMachine()
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
