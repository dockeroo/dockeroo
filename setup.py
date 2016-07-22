
# -*- coding: utf-8 -*-
# 
# Copyright (c) 2016, Giacomo Cariello. All rights reserved.

import os
import warnings
from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()
VERSION = '0.4'

requires = [
    'setuptools',
    'tzlocal',
    'shellescape',
    'zc.buildout',
    ]

warnings.filterwarnings('ignore', '.*', UserWarning, 'distutils.dist', 267)

setup(name='dockeroo',
    version=VERSION,
    description='Docker buildout recipe',
    long_description=README + '\n\n' +  CHANGES,
    classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: Apache Software License",
        "Development Status :: 4 - Beta",
        "Operating System :: OS Independent",
        "Framework :: Buildout",
        "Intended Audience :: Developers",
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
    test_suite="dockeroo",
    entry_points = {
        'zc.buildout': [
            'build = dockeroo.build:Recipe',
            'copy = dockeroo.copy:Recipe',
            'gentoo-bootstrap = dockeroo.gentoo_bootstrap:Recipe',
            'gentoo-build = dockeroo.gentoo_build:Recipe',
            'gentoo-diskimage = dockeroo.gentoo_diskimage:Recipe',
            'pull = dockeroo.pull:Recipe',
            'push = dockeroo.push:Recipe',
            'run = dockeroo.run:Recipe',
            'volume = dockeroo.volume:Recipe',
        ],
        'zc.buildout.uninstall': [
            'build = dockeroo.build:recipe._uninstall',
            'copy = dockeroo.copy:Recipe._uninstall',
            'gentoo-bootstrap = dockeroo.gentoo_bootstrap:Recipe._uninstall',
            'gentoo-build = dockeroo.gentoo_build:recipe._uninstall',
            'gentoo-diskimage = dockeroo.gentoo_diskimage:Recipe._uninstall',
            'pull = dockeroo.pull:Recipe._uninstall',
            'push = dockeroo.push:Recipe._uninstall',
            'run = dockeroo.run:Recipe._uninstall',
            'volume = dockeroo.volume:Recipe._uninstall',
        ],
    },
)
