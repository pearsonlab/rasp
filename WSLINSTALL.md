# RASP in Windows Subsystem for Linux

### This is a guide to installing and running RASP on Windows systems using Windows Subsystem for Linux (WSL)

<br>

# Setup
## I. Install WSL
After WSL installation, the WSL distro can be activated by the `wsl` command in Command Prompt.
1. Enable WSL via Powershell as administrator
    ```
    Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
    ```
2. Restart system
3. Install Ubuntu 18.04 (or other distro) from Windows Store
4. Initialize distro (set username, password)

## II. WSL File System
WSL files can be accessed by `~`, which is equivalent to `/home/[USER]`, within the WSL. Windows files, specifically the C: drive can be accessed through the path: `/mnt/c`. For RASP purposes, only the plasma store and the anaconda environment used to execute RASP is within the WSL system. The RASP program is located within Windows file system.

## III. Adding to PATH in WSL
1. Use vim to edit `~/.profile`
    ```
    vim ~/.profile
    ```
2. Add `export PATH="[PATH]:$PATH"` to end of `~/.profile` file
3. Restart WSL

## IV. Install Anaconda3 in WSL
1. Find latest version of Anaconda for Linux on https://repo.continuum.io/archive
2. Install latest version within WSL
    ```
    wget https://repo.continuum.io/archive/Anaconda3-[VERSION]-Linux-x86_64.sh
    ```
3. Run installation script
    ```
    bash Anaconda-[VERSION]-Linux-x86_64.sh
    ```
4. Opt to install Visual Studio Code
5. Add Anaconda to `$PATH` (see [Section III](#IV.-Install-Anaconda3-in-WSL))
    ```
    export PATH="~/anaconda3/bin:$PATH"
    ```

## V. Installing & Running X Server for GUI Framework
1. Download and install VcXsrv from https://sourceforge.net/projects/vcxsrv/
2. Run XLaunch
    - Set Display number to "0"
    - Select Disable access control
    - Keep other default settings
3. Allow access through Windows firewall if prompted
4. Set display when running RASP
    ```
    export DISPLAY=:0
    ```

## VI. Create CaImAn environment
1. Install CaImAn <br>
This creates a new anaconda environment named `caiman` using Python 3.6, which should be used for all future RASP installations and executions.
    ```
    git clone https://github.com/flatironinstitute/CaImAn
    cd CaImAn
    conda env create -f environment.yml -n caiman
    conda activate caiman
    pip install .
    ```

## VII. RASP Installation & Execution
1. Clone RASP
    ```
    git clone https://github.com/pearsonlab/rasp
    ```
2. Activate `caiman` environment 
    ```
    conda activate caiman
    ```
3. cd into `rasp/src` <br>
This step is not needed if `rasp` is added to the `$PYTHONPATH`
4. Turn on `plasma_store_server` <br>
`plasma_store_server` is most likely located in `~/anaconda3/envs/caiman/bin` <br>
This step is not needed if the path is hardcoded into `src/nexus.py`
    ```
    ./plasma_store_server -m [MEMORY AMOUNT] -s /tmp/store
    ```
5. Run XLaunch and set display (see [Section V](#V.-Installing-&-Running-X-Server-for-GUI-Framework))
    ```
    export DISPLAY=:0
    ```
6. Run RASP 
    ```
    python -m nexus.nexus
    ```
7. See [Common Issues](#Common-Issues) for errors and missing dependencies that might need to be installed, such as the following
    - pyarrow
    - pyqtgraph

<br>

# Common Issues
## I. WSL Installation from Windows Store
If Ubuntu cannot be downloaded and installed from the Windows Store, it can be instead manually downloaded and installed through the following instructions.

1. Go to https://docs.microsoft.com/en-us/windows/wsl/install-manual to download distro or https://aka.ms/wsl-ubuntu-1804 to directly download Ubuntu 18.04
2. If running the .appx file downloaded does not successfull install, rename .appx extension to .zip and uncompress
3. Run `ubuntu18.04.exe` or altenerative distro executable
4. Complete initialization and rest of installation

## II. CaImAn Installation
Several issues can appear during the CaImAn installation process. It is recommended that if any severe issues appear, one should delete and then recreate the caiman conda environment from scratch. Some of the following issues might appear:

1. `Aborted (core dumped)` when activating the `caiman` env
    - Solved by updating all packages
        ```
        conda update --all
        ```

## III. Errors Running RASP

1. `ImportError: libGl.so.1: cannot open shared object file`
    - Solved by running the following
        ```
        sudo apt-get update
        sudo apt-get install libgl1-mesa-glx
        ```

2. `ImportError: libopencv_reg.so.3.4: cannot enable executable stack as shared object`
    - Solved by running the following (second line contains path of opencv installation)
        ```
        sudo apt-get install execstack
        sudo execstack -c ~/anaconda3/envs/caiman/lib/libopencv_*
        ```
3. `This application failed to start because it could not find or load the Qt platform plugin "xcb"`
    - Solved by running the following
        ```
        sudo apt-get install libqt5x11extras5
        ```


