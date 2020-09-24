syncupd
====

Offload workload to another server by synchronizing the entire system up there.

Possible workloads are:
1. installing packages through building (especailly for Gentoo)
2. checking system integrity
3. playing game


Installation
===
Currently syncupd can only be installed on Gentoo Linux.

Steps:
1. add overlay https://github.com/fpemud/fpemud-overlay
2. emerge syncupd
3. emerge syncupd-plugin-gentoo (optional)
4. emerge syncupd-plugin-xrdp-games (optional)
5. systemctl enable syncupd
6. systemctl start syncupd


How does it work?
===

syncupd and it's client carry on the following operations:
1. sync up: create a disk image on server, rsync all system files of the client machine into it
2. execute: mount the disk image, using "ssh -t" to chroot execute a command (like "/usr/bin/emerge ...")
3. rsync down: rsync the content of the disk image back into the client machine

Step 1 may take hours on first use, but from the second time on it should take no time since the disk
image is cached on server.


Example
===
I have an ASUS T300chi, installs Gentoo. It is a fanless notepad which is not suitable to bear any
high work load.
Below is how I install www-client/firefox:


Security Consideration
===

Synchronize your system elsewhere is intriscally insecure.
You should take the following measurement to solve this problem:
1. exclude critical files (like /etc/shadow) from synchronizing on client side
2. deploy syncupd in local network 

TODO
===
1. cross-architecture-execution
   currently syncupd must be run on a machine which has the same or super architecure than the client machine
   in future, syncupd should auto create qemu virtual machine and cross-distcc to support cross architecure 
2. realtime sync down
   sync down after work is done has many disadvantanges
   use inotify techonology, so that sync down happens realtime
   it's hard work because it means I can't use rsync anymore for sync down, I must implement by myself.
