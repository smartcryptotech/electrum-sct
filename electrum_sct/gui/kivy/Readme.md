# Kivy GUI

The Kivy GUI is used with Electrum-SCT on Android devices.
To generate an APK file, follow these instructions.

## Android binary with Docker

This assumes an Ubuntu host, but it should not be too hard to adapt to another
similar system. The docker commands should be executed in the project's root
folder.

1. Install Docker

    ```
    $ curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    $ sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
    $ sudo apt-get update
    $ sudo apt-get install -y docker-ce
    ```

2. Build image

    ```
    $ sudo docker build -t electrum-android-builder-img electrum_sct/gui/kivy/tools
    ```

3. Build locale files

    ```
    $ ./contrib/make_locale
    ```

4. Prepare pure python dependencies

    ```
    $ ./contrib/make_packages
    ```

5. Build binaries

    ```
    $ sudo docker run -it --rm \
        --name electrum-android-builder-cont \
        -v $PWD:/home/user/wspace/electrum \
        -v ~/.keystore:/home/user/.keystore \
        --workdir /home/user/wspace/electrum \
        electrum-android-builder-img \
        ./contrib/make_apk
    ```
    This mounts the project dir inside the container,
    and so the modifications will affect it, e.g. `.buildozer` folder
    will be created.

5. The generated binary is in `./bin`.



## FAQ

### I changed something but I don't see any differences on the phone. What did I do wrong?
You probably need to clear the cache: `rm -rf .buildozer/android/platform/build/{build,dists}`


### How do I deploy on connected phone for quick testing?
Assuming `adb` is installed:
```
$ adb -d install -r bin/Electrum-*-debug.apk
$ adb shell monkey -p org.newyorkcoin.electrum_sct.electrum_sct 1
```


### How do I get an interactive shell inside docker?
```
$ sudo docker run -it --rm \
    -v $PWD:/home/user/wspace/electrum \
    --workdir /home/user/wspace/electrum \
    electrum-android-builder-img
```


### How do I get more verbose logs?
See `log_level` in `buildozer.spec`


### Kivy can be run directly on Linux Desktop. How?
Install Kivy.

Build atlas: `(cd electrum_sct/gui/kivy/; make theming)`

Run electrum-sct with the `-g` switch: `electrum-sct -g kivy`
