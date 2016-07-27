
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
import warnings
from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()
VERSION = '0.17'

requires = [
    'decorator',
    'future',
    'setuptools',
    'shellescape',
    'tzlocal',
    'zc.buildout',
    ]

warnings.filterwarnings('ignore', '.*', UserWarning, 'distutils.dist', 267)

setup(name='dockeroo',
    version=VERSION,
    description='Docker buildout recipe',
    long_description=README + '\n\n' +  CHANGES,
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Development Status :: 4 - Beta",
        "Operating System :: OS Independent",
        "Framework :: Buildout",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
    ],
    author='Giacomo Cariello',
    author_email='info@dockeroo.com',
    url='http://dockeroo.com/',
    download_url='https://github.com/dockeroo/dockeroo/tarball/{version}'.format(version=VERSION),
    keywords=['buildout', 'docker'],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    tests_require=requires,
    test_suite="tests.tests",
    entry_points = {
        'zc.buildout': [
            'docker.build = dockeroo.docker.build:DockerBuildRecipe',
            'docker.copy = dockeroo.docker.copy:DockerCopyRecipe',
            'docker.gentoo-bootstrap = dockeroo.docker.gentoo_bootstrap:DockerGentooBootstrapRecipe',
            'docker.gentoo-build = dockeroo.docker.gentoo_build:DockerGentooBuildRecipe',
            'docker.gentoo-diskimage = dockeroo.docker.gentoo_diskimage:DockerGentooDiskImageRecipe',
            'docker.network = dockeroo.docker.network:DockerNetworkRecipe',
            'docker.pull = dockeroo.docker.pull:DockerPullRecipe',
            'docker.push = dockeroo.docker.push:DockerPushRecipe',
            'docker.run = dockeroo.docker.run:DockerRunRecipe',
            'docker.volume = dockeroo.docker.volume:DockerVolumeRecipe',
            'setup.download = dockeroo.setup.download:DockerSetupDownloadRecipe',
            'setup.cmmi = dockeroo.setup.cmmi:DockerSetupCmmiRecipe',
            'setup.egg = dockeroo.setup.egg:DockerSetupEggRecipe',
            'setup.script = dockeroo.setup.script:DockerSetupScriptRecipe',
        ],
        'zc.buildout.uninstall': [
            'docker.build = dockeroo.docker.build:DockerBuildRecipe._uninstall',
            'docker.copy = dockeroo.docker.copy:DockerCopyRecipe._uninstall',
            'docker.gentoo-bootstrap = dockeroo.docker.gentoo_bootstrap:DockerGentooBootstrapRecipe._uninstall',
            'docker.gentoo-build = dockeroo.docker.gentoo_build:DockerGentooBuildRecipe._uninstall',
            'docker.gentoo-diskimage = dockeroo.docker.gentoo_diskimage:DockerGentooDiskImageRecipe._uninstall',
            'docker.network = dockeroo.docker.network:DockerNetworkRecipe._uninstall',
            'docker.pull = dockeroo.docker.pull:DockerPullRecipe._uninstall',
            'docker.push = dockeroo.docker.push:DockerPushRecipe._uninstall',
            'docker.run = dockeroo.docker.run:DockerRunRecipe._uninstall',
            'docker.volume = dockeroo.docker.volume:DockerVolumeRecipe._uninstall',
            'setup.download = dockeroo.setup.download:DockerSetupDownloadRecipe._uninstall',
            'setup.cmmi = dockeroo.setup.cmmi:DockerSetupCmmiRecipe._uninstall',
            'setup.egg = dockeroo.setup.egg:DockerSetupEggRecipe._uninstall',
            'setup.script = dockeroo.setup.script:DockerSetupScriptRecipe._uninstall',
        ],
    },
)
