## An alternate UI for x42-nodes.  

This was initially developed to offer a quick dashboard view for a headless node running on your network.  For instance, if you are running a full-node on resource limited hardware (such as a raspberry pi) this dashboard will allow you to view the status of that node from another machine.  In its current form, this UI assumes you already have an x42-node up and running somewhere on your network.  If you need assistance setting up a node, reference the following links.

  *[Official X42](https://github.com/x42protocol/X42-FullNode)
  *[Headless setup](https://www.reddit.com/r/x42/comments/akp6lp/creating_a_headless_staking_node_on_ubuntu_1804/?utm_source=share&utm_medium=web2x)
  *[Full-Node on RaspPi setup](https://www.reddit.com/r/x42/comments/catbin/raspberry_pi_3_build/?utm_source=share&utm_medium=web2x)

This project was developed using python v3.7.4 and PySide2 v5.12.3.  Built/packaged with [fbs](https://build-system.fman.io/manual/).

![x42lite Dashboard](https://i.imgur.com/oMEJCTp.gif)

## To Install:
Simply download the appropriate installer for your platform from the [installers](https://github.com/jb41997/x42lite/tree/master/installers) directory.

If the node is on another machine, see the "For nodes not running on your local machine" section below.

## To compile from source:

First install python 3 if you haven't already.  (Version 3.5,3.6, or 3.7 should work)

Next, create a directory where you want the project to live.
```
mkdir x42lite
cd x42lite
```
Now create a virtual environment:
```
python3 -m venv venv
```

Activate the Virtual environment:
```
#Mac/linux:
source venv/bin/activate
#windows:
call venv\scripts\activate.bat
```
Install fbs, pyside2 and requests-futures:
```
pip install fbs PySide2==5.12.3 requests-futures
```
If that produced errors, try installing wheel first:
```
pip install wheel
```

Now we should be ready to clone the repository (or download zip and extract into the current directory):
```
git clone https://github.com/jb41997/x42lite.git
cd x42lite
```

If the node is running on your current machine then all you should have to do is issue the following command to test the UI.  (If your node is running on a different machine, see below.)
```
fbs run
```

If you would like to build a standalone executable for your current platform follow the steps [here](https://github.com/mherrmann/fbs-tutorial).

## For nodes not running on your local machine:

First make sure your node is able to talk on the network.  Log in to the node machine (or ssh) and navigate to the x42.conf file.  If you followed one of the headless setup guides mentioned at the top of this page, then the file will be located here:  ```~/.x42node/x42/x42Main/``` . Or on windows I believe its located here: ```%APPDATA%\x42Node\x42\x42Main```.

We need to edit that x42.conf file.  
For instance, linux/mac users can simply
 ```
 cd ~/.x42node/x42/x42Main/
 nano x42.conf
 ```
Scroll to the ```###API Settings###``` section towards the bottom of the file.  Find, uncomment, and set 
```apiuri=http://0.0.0.0```.
Save the edits and close.  Then bounce (stop/start) the node.  What this has done is allowed your nodes swagger api to be accessible on port 42220 from other machines on your network.  

Now back in the application you should be able to adjust the IP settings to your node machine.

(If x42lite is still having problems connecting to your node, you may need to adjust firewall settings etc.)


## x42lite is currently in Beta pending interest from the community.  Feel free to submit an issue for bugs and suggestions.


