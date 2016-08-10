========
dockeroo
========

dockeroo is a series of buildout_ recipes to build and manage docker containers and docker hosts.

dockeroo can build docker images from a classic Dockerfile or use a Gentoo_ container to assemble multiple Gentoo binary packages into a docker image.

.. _buildout: http://www.buildout.org/
.. _Gentoo: http://www.gentoo.org/


Useful links
============

* PyPI page: https://pypi.python.org/pypi/dockeroo/
* Code repository: https://github.com/dockeroo/dockeroo


Documentation
=============

Documentation is available at the following address:

https://pythonhosted.org/dockeroo/


Bug reports and Feedback
========================

Please don't hesitate to give feedback and especially report bugs or ask for new features on GitHub issue tracker:

https://github.com/dockeroo/dockeroo/issues


License
=======

Copyright © 2016, Giacomo Cariello <info@dockeroo.com>

dockeroo is released under Apache 2.0 License. See `LICENSE.rst`_ for complete license.

.. _LICENSE.rst: https://github.com/dockeroo/dockeroo/blob/master/LICENSE.rst


Status
======

dockeroo is beta software.


Recipes
=======

Docker recipes
--------------

* `dockeroo:docker.build <https://pythonhosted.org/dockeroo/docker.html#module-dockeroo.docker.build>`_
* `dockeroo:docker.copy <https://pythonhosted.org/dockeroo/docker.html#module-dockeroo.docker.copy>`_
* `dockeroo:docker.gentoo-bootstrap <https://pythonhosted.org/dockeroo/docker.html#module-dockeroo.docker.gentoo_bootstrap>`_
* `dockeroo:docker.gentoo-build <https://pythonhosted.org/dockeroo/docker.html#module-dockeroo.docker.gentoo_build>`_
* `dockeroo:docker.gentoo-diskimage <https://pythonhosted.org/dockeroo/docker.html#module-dockeroo.docker.gentoo_diskimage>`_
* `dockeroo:docker.network <https://pythonhosted.org/dockeroo/docker.html#module-dockeroo.docker.network>`_
* `dockeroo:docker.pull <https://pythonhosted.org/dockeroo/docker.html#module-dockeroo.docker.pull>`_
* `dockeroo:docker.push <https://pythonhosted.org/dockeroo/docker.html#module-dockeroo.docker.push>`_
* `dockeroo:docker.run <https://pythonhosted.org/dockeroo/docker.html#module-dockeroo.docker.run>`_
* `dockeroo:docker.volume <https://pythonhosted.org/dockeroo/docker.html#module-dockeroo.docker.volume>`_

Docker Machine recipes
----------------------

* `dockeroo:machine.create <https://pythonhosted.org/dockeroo/docker_machine.html#module-dockeroo.machine.create>`_

Setup recipes
-------------

* `dockeroo:setup.cmmi <https://pythonhosted.org/dockeroo/setup.html#module-dockeroo.setup.cmmi>`_
* `dockeroo:setup.download <https://pythonhosted.org/dockeroo/setup.html#module-dockeroo.setup.download>`_
* `dockeroo:setup.egg <https://pythonhosted.org/dockeroo/setup.html#module-dockeroo.setup.egg>`_
* `dockeroo:setup.python-script <https://pythonhosted.org/dockeroo/setup.html#module-dockeroo.setup.python_script>`_
* `dockeroo:setup.shell-script <https://pythonhosted.org/dockeroo/setup.html#module-dockeroo.setup.shell_script>`_
* `dockeroo:setup.template <https://pythonhosted.org/dockeroo/setup.html#module-dockeroo.setup.template>`_
