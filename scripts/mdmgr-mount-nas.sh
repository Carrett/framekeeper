#!/bin/sh
# Fixed mount command, no arguments accepted. Installed as root:root 755 by install_sudoers.sh.
exec /usr/sbin/mount.cifs //@NAS_HOST@/@NAS_SHARE@ @MOUNT_POINT@ \
  -o credentials=@CREDENTIALS_FILE@,vers=3.0,uid=@UID@,gid=@GID@,iocharset=utf8,file_mode=0755,dir_mode=0755
