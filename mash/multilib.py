# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from fnmatch import fnmatch

class MultilibMethod:
    def __init__(self, dummy):
        self.name = 'base'
    def select(self, po):
        prefer_64 = [ 'gdb', 'frysk', 'systemtap', 'systemtap-runtime', 'ltrace', 'strace' ]
        if po.arch.find('64') != -1:
            if po.name in prefer_64:
                return True
            if po.name.startswith('kernel'):
                for (p_name, p_flag, (p_e, p_v, p_r)) in po.provides:
                    if p_name == 'kernel' or p_name == 'kernel-devel':
                        return True
        return False

class NoMultilibMethod:
    def __init__(self, dummy):
        self.name = 'none'
        
    def select(self, po):
        return False

class AllMultilibMethod(MultilibMethod):
    def __init__(self, dummy):
        self.name = 'all'
    
    def select(self, po):
        return True
    
class FileMultilibMethod(MultilibMethod):
    def __init__(self, file):
        self.name = 'file'
        self.list = []
        if file:
            f = open(file,'r')
            lines = f.readlines()
            f.close()
            for line in lines:
                line = line.strip()
                if not line.startswith('#'):
                    self.list.append(line)
    
    def select(self, po):
        for item in self.list:
            if fnmatch(po.name, item):
                return True
        return False

class KernelMultilibMethod:
    def __init__(self, dummy):
        self.name = 'base'
    def select(self, po):
        if po.arch.find('64') != -1:
            if po.name.startswith('kernel'):
                for (p_name, p_flag, (p_e, p_v, p_r)) in po.provides:
                    if p_name == 'kernel' or p_name == 'kernel-devel':
                        return True
        return False
            
class RuntimeMultilibMethod(MultilibMethod):
    def __init__(self, dummy):
        self.name = 'runtime'
    
    def select(self, po):
        libdirs = [ '/usr/lib', '/usr/lib64', '/lib', '/lib64' ]
        blacklist = [ 'tomcat-native' ]
        whitelist = [ 'libgnat', 'wine', 'lmms-vst', 'nspluginwrapper', 'libflashsupport', 'pulseaudio-utils', 'valgrind', 'perl-libs' ]
        if po.name in blacklist:
            return False
        if po.name in whitelist:
            return True
        if MultilibMethod.select(self,po):
            return True
        if po.name.startswith('kernel'):
            for (p_name, p_flag, (p_e, p_v, p_r)) in po.provides:
                if p_name == 'kernel':
                    return False
        for file in po.returnFileEntries():
            (dirname, filename) = file.rsplit('/', 1)
            # libraries in standard dirs
            if dirname in libdirs and fnmatch(filename, '*.so.*'):
                return True
            # dri
            if dirname in [ '/usr/lib/dri', '/usr/lib64/dri' ]:
                return True
            # krb5
            if dirname in [ '/usr/lib/krb5/plugins', '/usr/lib64/krb5/plugins' ]:
                return True
            # pam
            if dirname in [ '/lib/security', '/lib64/security' ]:
                return True
            # sasl
            if dirname in [ '/usr/lib/sasl2', '/usr/lib64/sasl2' ]:
                return True
            # nss
            if dirname in [ '/lib', '/lib64' ] and filename.startswith('libnss_'):
                return True
            # alsa
            if dirname in [ '/usr/lib/alsa-lib', '/usr/lib64/alsa-lib' ]:
                return True
            # lsb
            if dirname == '/etc/lsb-release.d':
                return True
            # mysql, qt, etc.
            if dirname == '/etc/ld.so.conf.d' and filename.endswith('.conf'):
                return True
	    # gtk2-engines
	    if fnmatch(dirname, '/usr/lib*/gtk-2.0/*/engines'):
		return True
            # accessibility
            if fnmatch(dirname, '/usr/lib*/gtk-2.0/modules'):
                return True
            if fnmatch(dirname, '/usr/lib*/gtk-2.0/*/modules'):
                return True
	    # scim-bridge-gtk	
            if fnmatch(dirname, '/usr/lib*/gtk-2.0/immodules'):
                return True
            if fnmatch(dirname, '/usr/lib*/gtk-2.0/*/immodules'):
                return True
            # images
            if fnmatch(dirname, '/usr/lib*/gtk-2.0/*/loaders'):
                return True
            if fnmatch(dirname, '/usr/lib*/gdk-pixbuf-2.0/*/loaders'):
                return True
            if fnmatch(dirname, '/usr/lib*/gtk-2.0/*/printbackends'):
                return True
            if fnmatch(dirname, '/usr/lib*/gtk-2.0/*/filesystems'):
                return True
            # qt/kde fun
            if fnmatch(dirname, '/usr/lib*/qt*/plugins/*'):
                return True
            if fnmatch(dirname, '/usr/lib*/kde*/plugins/*'):
                return True
            # gstreamer
            if fnmatch(dirname, '/usr/lib*/gstreamer-*'):
                return True
            # xine-lib
            if fnmatch(dirname, '/usr/lib*/xine/plugins/*'):
                return True
            # oprofile
            if fnmatch(dirname, '/usr/lib*/oprofile') and fnmatch(filename, '*.so.*'):
                return True
            # wine
            if fnmatch(dirname, '/usr/lib*/wine') and filename.endswith('.so'):
                return True
            # db
            if dirname in [ '/lib', '/lib64' ] and filename.startswith('libdb-'):
                return True
            # sane drivers
            if dirname in [ '/usr/lib/sane', '/usr/lib64/sane' ] and filename.startswith('libsane-'):
                return True
        return False

class DevelMultilibMethod(RuntimeMultilibMethod):
    def __init__(self, dummy):
        self.name = 'devel'
    
    def select(self, po):
        blacklist = ['dmraid-devel', 'kdeutils-devel', 'mkinitrd-devel', 'java-1.5.0-gcj-devel', 'java-1.7.0-icedtea-devel', 'php-devel', 'java-1.6.0-openjdk-devel',
                     'java-1.7.0-openjdk-devel' ]
        whitelist = ['glibc-static', 'libstdc++-static']
        if po.name in blacklist:
            return False
        if po.name in whitelist:
            return True
        if RuntimeMultilibMethod.select(self,po):
            return True
        if po.name.startswith('kernel'):
            for (p_name, p_flag, (p_e, p_v, p_r)) in po.provides:
                if p_name == 'kernel-devel':
                    return False
        if po.name.startswith('ghc-'):
            return False
        if po.name.endswith('-devel'):
            return True
        return False

