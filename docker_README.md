# Docker Image Creation

A docker image can be generated from the `Dockerfile` using the following command. Go to the folder containing the `Dockerfile`

```bash
docker build . -t improv
```

The most complicated part is the piping of GUI from the Docker instance to the host system.

## Windows 10
Tested on Windows 10 Build 18990, Docker Desktop v.2.1.2.0 Tech Preview, and WSL 2 with Ubuntu 18.04 distro.

[Wiki page](https://github.com/pearsonlab/improv/wiki/Docker)

#### First time
Note that the following is only needed for GUI access.

1. Install `XWindow`

    Make sure that `XWindow` is running, and run

    ```bash
    docker run -it --rm --shm-size=16g improv
    ```

## Ubuntu

Tested on Ubuntu 19.10, Docker Engine version 19.03.5

#### First time
1. Install [Docker](https://docs.docker.com/install/linux/docker-ce/ubuntu/)

#### Run
1. Grant Docker access to X11 for GUI
    ```bash
    xhost +local:docker
    ```

2. Run Docker image
    ```bash
    sudo docker run -ti --rm -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY --shm-size=8g improv
    ```

## macOS 10.15 Catalina

Tested on macOS 10.15.1, Docker Desktop for macOS version 2.1.0.5 (40693)

#### First time
Note that the following is only needed for GUI access. [Reference](https://cntnr.io/running-guis-with-docker-on-mac-os-x-a14df6a76efc)

1. Install [Docker](https://docs.docker.com/docker-for-mac/install/)

2. Install Command Line Tools for Xcode.
    ```bash
    xcode-select --install
    ```

3. Install `Homebrew`.
    ```bash
    /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
    ```

4. Install `socat` and `XQuartz`.
    ```bash
    brew install socat
    brew install xquartz
    ```

5. Edit `XQuartz` security settings.
    ```bash
    open -a Xquartz
    ```
    > A white terminal window will pop up. Now open up the preferences from the top menu and go to the last tab ‘security’. There we need to make sure the “allow connections from network clients” is checked “on”.

#### Run
1. Quit `XQuartz` if started. Open a port to receive incoming signal.  **`socat` must be running prior to `XQuartz`.**

    ```bash
    socat TCP-LISTEN:6000,reuseaddr,fork UNIX-CLIENT:\"$DISPLAY\"
    ```
    Keep this terminal window open throughout the session.

2. Launch `XQuartz`
    ```bash
    open -a Xquartz
    ```

3. Launch a new terminal and start the Docker container.

    > We need the ip of the network interface of our host OS. Then we pass that on as the `DISPLAY` environment variable in the Docker container that runs the graphical interface.

    ```bash
    ip=$(ifconfig en0 | awk '/inet / {print $2; }')
    docker run -it --rm --shm-size=8g -e DISPLAY=$ip:0 improv
    ```
