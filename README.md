# obs-monitor-scene-switcher
a plugin for OBS that will swap the scene based on what monitor the mouse is currently in

### Installing
* Download and install Python 3.6 - [Link](https://www.python.org/downloads/release/python-368/)
* With the Python3.6 pip, install requirements.txt: `python -m pip -r ./requirements.txt`
  * I don't have python3.6 in my PATH, you may need to call it directly where it's installed.
* In OBS's "Scripts" window, link Python3.6 through the "Python Settings" tab
* In the "Scripts" tab click the `+` button and select `monitor-screen-switcher.py` to load the script
* Select what monitors you want to tie to which scene, scenes will now transition when you're in that monitor