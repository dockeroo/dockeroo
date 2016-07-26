
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
VERSION = '0.16'

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
            'docker.build = dockeroo.docker.build:Recipe',
            'docker.copy = dockeroo.docker.copy:Recipe',
            'docker.gentoo-bootstrap = dockeroo.docker.gentoo_bootstrap:Recipe',
            'docker.gentoo-build = dockeroo.docker.gentoo_build:Recipe',
            'docker.gentoo-diskimage = dockeroo.docker.gentoo_diskimage:Recipe',
            'docker.network = dockeroo.docker.network:Recipe',
            'docker.pull = dockeroo.docker.pull:Recipe',
            'docker.push = dockeroo.docker.push:Recipe',
            'docker.run = dockeroo.docker.run:Recipe',
            'docker.volume = dockeroo.docker.volume:Recipe',
            'setup.download = dockeroo.setup.download:Recipe',
            'setup.cmmi = dockeroo.setup.cmmi:Recipe',
            'setup.egg = dockeroo.setup.egg:Recipe',
            'setup.script = dockeroo.setup.script:Recipe',
        ],
        'zc.buildout.uninstall': [
            'docker-build = dockeroo.docker.build:Recipe._uninstall',
            'docker-copy = dockeroo.docker.copy:Recipe._uninstall',
            'docker-gentoo-bootstrap = dockeroo.docker.gentoo_bootstrap:Recipe._uninstall',
            'docker-gentoo-build = dockeroo.docker.gentoo_build:Recipe._uninstall',
            'docker-gentoo-diskimage = dockeroo.docker.gentoo_diskimage:Recipe._uninstall',
            'docker-network = dockeroo.docker.network:Recipe._uninstall',
            'docker-pull = dockeroo.docker.pull:Recipe._uninstall',
            'docker-push = dockeroo.docker.push:Recipe._uninstall',
            'docker-run = dockeroo.docker.run:Recipe._uninstall',
            'docker-volume = dockeroo.docker.volume:Recipe._uninstall',
            'build-download = dockeroo.build.download:BuildDownloadRecipe._uninstall',
        ],
    },
)
