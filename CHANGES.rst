Changelog
=========

0.30 (10-10-2016)
-----------------

- Fixed dockeroo:gentoo-build "volumes" parameter declaration.


0.29 (26-09-2016)
-----------------

- Updated dockeroo:gentoo-build add_package_modifier() to support package.* folders.


0.28 (21-09-2016)
-----------------

- Fixed dockeroo:gentoo-build which didn't account for empty build dependencies.


0.27 (21-09-2016)
-----------------

- Added support for post-build-{script,shell,script} parameters on dockeroo:gentoo-build recipe.
  IMPORTANT: build-script stage has been anticipated and now its previous stage has been replaced by
  post-build-script.


0.26 (19-09-2016)
-----------------

- Added support for pre-build-{script,shell,script} parameters on dockeroo:gentoo-build recipe.


0.25 (17-09-2016)
-----------------

- Fixed config_binfmt to execute commands through sudo.


0.24 (17-09-2016)
-----------------

- Added initial support for processor function upon copy path.
- Moved config_binfmt support to DockerMachine.


0.23 (15-09-2016)
-----------------

- Included freeze in release MANIFEST.in.


0.22 (14-08-2016)
-----------------

- Bugfix release.


0.21 (10-08-2016)
-----------------

- Updated dockeroo:setup.template to handle default output-path.
- Improved handling of recipe default location.
- Several bug fixes.


0.20 (08-08-2016)
-----------------

- Introduced sphinx documentation and moved recipes documentation to respective
  classes docstrings.
- Fixed dockeroo:machine.create recipe.


0.19 (31-07-2016)
-----------------

- Added dockeroo:setup.template recipe.
- Added support for render_template filterset.
- Added dockeroo:setup.shell-script and dockeroo:machine.create recipes.
- Removed "decorator" dependency, we're handling everything with functools.wraps.


0.18 (28-07-2016)
-----------------

- Minor documentation fixes.


0.17 (24-07-2016)
-----------------

- Added dockeroo.setup recipes.
- Refactored testing.
- Renamed all recipes.
- Major round of refactoring/convention check.


0.16 (24-07-2016)
-----------------

- Split DockerMachine and DockerEngine.
- Fixed CHANGELOG.rst formatting.
- Fixed get_random_name().


0.15 (24-07-2016)
-----------------

- Minor fixes.


0.14 (24-07-2016)
-----------------

- Minor fixes.


0.13 (24-07-2016)
-----------------

- Added keep option to **docker:pull**.
- update() methods now check wether target has to be rebuilt.


0.12 (23-07-2016)
-----------------

- Minor fix to **docker:run**.


0.11 (23-07-2016)
-----------------

- Renamed primary option to "name" for all recipes.
- Renamed "machine" option to "machine-name".


0.10 (23-07-2016)
-----------------

- Minor fix to **docker:run**.


0.9 (23-07-2016)
----------------

- Updated **machine_name** selection: if **machine** option is not set
  DOCKER_MACHINE_NAME environment variable is used, or "default" if unset.
- Added support for option **start** in **docker:run**.


0.8 (23-07-2016)
----------------

- Added support for Python 3.
- Added initial support for unit tests.


0.7 (22-07-2016)
----------------

- Fixed **dockeroo:run** ip address fetch.


0.6 (22-07-2016)
----------------

- Updated documentation.
- Added support for networks, network-aliases and links
  on **dockeroo:run**.
- Added new recipe **dockeroo:network**.


0.5 (22-07-2016)
----------------

- Added support for environment variables and ports
  on **dockeroo:run**.


0.3 (22-07-2016)
----------------

- Fixed MANIFEST.in.


0.1 (22-07-2016)
----------------

- Initial release.
