====================================
Welcome to dockeroo's documentation!
====================================

dockeroo is a series of buildout_ recipes to build and manage docker containers and docker hosts.

dockeroo can build docker images from a classic Dockerfile or use a Gentoo_ container to assemble multiple Gentoo binary packages into a docker image.

.. _buildout: http://www.buildout.org/
.. _Gentoo: http://www.gentoo.org/


Useful links
============

* PyPI page: https://pypi.python.org/pypi/dockeroo/
* Code repository: https://github.com/dockeroo/dockeroo


Bug reports and Feedback
========================

Please don't hesitate to give feedback and especially report bugs or ask for new features on GitHub issue tracker:

https://github.com/dockeroo/dockeroo/issues


License
=======

Copyright © 2016, Giacomo Cariello <info@dockeroo.com>

dockeroo is released under Apache 2.0 License. See `LICENSE.rst`_ for complete license.

.. _LICENSE.rst: https://github.com/dockeroo/dockeroo/blob/master/LICENSE.rst


Requirements
============

dockeroo requires a working buildout environment and the following system packages:

* docker >= 1.11
* docker-machine >= 0.7.0


Contents
========

.. toctree::
   :maxdepth: 2

   docker
   docker_machine
   setup



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

