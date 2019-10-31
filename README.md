syncupd
====

Offload the workload to the cloud by synchronizing the entire system up there.

Valid workloads are:
1. installing packages through building (especailly for Gentoo user, like me)
2. checking system integrity
3. 


Installation
===
Currently syncupd can only installs on Gentoo.

1. add overlay https://github.com/fpemud/fpemud-overlay
2. emerge syncupd
3. systemctl enable syncupd
4. systemctl start syncupd

Rationale
===

syncupd client create a ssl connection to interact control message with server.
use 3 dynamical services:
1. rsync service: sync up
2. ssh service: do real work and interact with user
3. rsync service: sync down
4. catfile serivce: get the content of the specified file on server

syncupd creates an disk image with ext4 filesystem in /var/cache/syncupd.
when client connects, syncupd auto mount this disk image as /var/cache/syncupd/XXX/mntdir, chroot into
it and run the user command.

sync up would cause hours when first use it.
but from the second time on syncup should take no time unless your system has a big change.


Example
===
I have an ASUS T300chi, installs Gentoo. It is a fanless notepad not able to bear high work load.
Below is how I install www-client/firefox:


Security Consideration
===

Synchronize your system elsewhere is intriscally insecure.
You should take the following measurement to solve this problem:
1. exclude critical files from synchronizing on client side, like /etc/shadow
2. deploy syncupd in local network 

TODO
===
1. cross-compiling
   currently syncupd must be run on a machine which has the same or super architecure than the client machine
   in future, syncupd should auto create qemu virtual machine and cross-distcc to support cross architecure 
2. realtime sync down
   sync down after work is done has many disadvantanges
   use inotify techonology, so that sync down happens realtime
   it's hard work because it means I can't use rsync anymore for sync down, I must implement by myself.
