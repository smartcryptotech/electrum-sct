#!/bin/bash

# Please update these carefully, some versions won't work under Wine
NSIS_FILENAME=nsis-3.04-setup.exe
NSIS_URL=https://prdownloads.sourceforge.net/nsis/$NSIS_FILENAME?download

ZBAR_FILENAME=zbarw-20121031-setup.exe
ZBAR_URL=https://sourceforge.net/projects/zbarw/files/$ZBAR_FILENAME/download

LIBUSB_FILENAME=libusb-1.0.22.7z
LIBUSB_URL=https://prdownloads.sourceforge.net/project/libusb/libusb-1.0/libusb-1.0.22/$LIBUSB_FILENAME?download

PYTHON_VERSION=3.6.8

## These settings probably don't need change
export WINEPREFIX=/opt/wine64
#export WINEARCH='win32'

PYTHON_FOLDER="python3"
PYHOME="c:/$PYTHON_FOLDER"
PYTHON="wine $PYHOME/python.exe -OO -B"


# Let's begin!
here="$(dirname "$(readlink -e "$0")")"
set -e

. $here/../build_tools_util.sh

wine 'wineboot'


cd /tmp/electrum-build

# Install Python
# note: you might need "sudo apt-get install dirmngr" for the following
# keys from https://www.python.org/downloads/#pubkeys
for msifile in core dev exe lib pip tools; do
    echo "Installing $msifile..."
    wget -N -c "https://www.python.org/ftp/python/$PYTHON_VERSION/win32/${msifile}.msi"
    wget -N -c "https://www.python.org/ftp/python/$PYTHON_VERSION/win32/${msifile}.msi.asc"
    wine msiexec /i "${msifile}.msi" /qb TARGETDIR=$PYHOME
done

# Install dependencies specific to binaries
# note that this also installs pinned versions of both pip and setuptools
$PYTHON -m pip install -r "$here"/../deterministic-build/requirements-binaries.txt

# Install PyInstaller
$PYTHON -m pip install pyinstaller==3.4 --no-use-pep517

# Install ZBar
download_if_not_exist $ZBAR_FILENAME "$ZBAR_URL"
wine "$PWD/$ZBAR_FILENAME" /S

# Install NSIS installer
download_if_not_exist $NSIS_FILENAME "$NSIS_URL"
wine "$PWD/$NSIS_FILENAME" /S

download_if_not_exist $LIBUSB_FILENAME "$LIBUSB_URL"
7z x -olibusb $LIBUSB_FILENAME -aoa

cp libusb/MS32/dll/libusb-1.0.dll $WINEPREFIX/drive_c/$PYTHON_FOLDER/

mkdir -p $WINEPREFIX/drive_c/tmp
cp secp256k1/libsecp256k1.dll $WINEPREFIX/drive_c/tmp/

echo "Wine is configured."
