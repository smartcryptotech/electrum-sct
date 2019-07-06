Electrum-SCT - Lightweight SmartCryptoTech client
=====================================

::

  Licence: GNU GPLv3+ for Electrum-DOGE components; CC BY 4.0 for SmartCryptoTech logo, MIT Licence for all other components
  Author: The SmartCryptoTech developers; based on Electrum by Thomas Voegtlin and Electrum-DOGE by The Electrum-DOGE contributors
  Language: Python (>= 3.6)
  Homepage: https://www.smartcryptotech.org/ ; original Electrum Homepage at https://electrum.org/


.. image:: https://travis-ci.org/CryptoLover705/electrum-sct.svg?branch=master
    :target: https://travis-ci.org/CryptoLover705/electrum-sct
    :alt: Build Status
.. image:: https://coveralls.io/repos/github/CryptoLover705/electrum-sct/badge.svg?branch=master
    :target: https://coveralls.io/github/CryptoLover705/electrum-sct?branch=master
    :alt: Test coverage statistics
.. image:: https://d322cqt584bo4o.cloudfront.net/electrum/localized.svg
    :target: https://crowdin.com/project/electrum
    :alt: Help translate Electrum online





Getting started
===============

Electrum-SCT is a pure python application. If you want to use the
Qt interface, install the Qt dependencies::

    sudo apt-get install python3-pyqt5

If you downloaded the official package (tar.gz), you can run
Electrum-SCT from its root directory without installing it on your
system; all the python dependencies are included in the 'packages'
directory. To run Electrum-SCT from its root directory, just do::

    ./run_electrum_sct

You can also install Electrum-SCT on your system, by running this command::

    sudo apt-get install python3-setuptools
    python3 -m pip install .[fast]

This will download and install the Python dependencies used by
Electrum-SCT instead of using the 'packages' directory.
The 'fast' extra contains some optional dependencies that we think
are often useful but they are not strictly needed.

If you cloned the git repository, you need to compile extra files
before you can run Electrum-SCT. Read the next section, "Development
Version".



Development version
===================

Check out the code from GitHub::

    git clone git://github.com/CryptoLover705/electrum-sct.git
    cd electrum-sct

Run install (this should install dependencies)::

    python3 -m pip install .[fast]


Compile the protobuf description file::

    sudo apt-get install protobuf-compiler
    protoc --proto_path=electrum_sct --python_out=electrum_sct electrum_sct/paymentrequest.proto

Create translations (optional)::

    sudo apt-get install python-requests gettext
    ./contrib/make_locale




Creating Binaries
=================

Linux
-----

See :code:`contrib/build-linux/README.md`.


Mac OS X / macOS
----------------

See :code:`contrib/osx/README.md`.


Windows
-------

See :code:`contrib/build-wine/docker/README.md`.


Android
-------

See :code:`electrum_sct/gui/kivy/Readme.md`.




