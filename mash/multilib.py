# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

from fnmatch import fnmatch

class MultilibMethod:
    def __init__(self):
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
    def __init__(self):
        self.name = 'none'
        
    def select(self, po):
        return False

class AllMultilibMethod(MultilibMethod):
    def __init__(self):
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
                    list.append(line)
    
    def select(self, po):
        for item in self.list:
            if fnmatch(po.name, item):
                return True
        return False

class KernelMultilibMethod:
    def __init__(self):
        self.name = 'base'
    def select(self, po):
        if po.arch.find('64') != -1:
            if po.name.startswith('kernel'):
                for (p_name, p_flag, (p_e, p_v, p_r)) in po.provides:
                    if p_name == 'kernel' or p_name == 'kernel-devel':
                        return True
        return False
            
class RuntimeMultilibMethod(MultilibMethod):
    def __init__(self):
        self.name = 'runtime'
    
    def select(self, po):
        libdirs = [ '/usr/lib', '/usr/lib64', '/lib', '/lib64' ]
        blacklist = [ 'tomcat-native' ]
        whitelist = [ 'libgnat', 'wine', 'wine-arts', 'lmms-vst', 'nspluginwrapper', 'libflashsupport', 'pulseaudio-utils', 'valgrind' ]
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
            # mysql, qt, etc.
            if dirname == '/etc/ld.so.conf.d' and filename.endswith('.conf'):
                return True
	    # gtk2-engines
	    if fnmatch(dirname, '/usr/lib*/gtk-2.0/*/engines'):
		return True
            # accessibility
            if fnmatch(dirname, '/usr/lib*/gtk-2.0/modules'):
                return True
	    # scim-bridge-gtk	
            if fnmatch(dirname, '/usr/lib*/gtk-2.0/immodules'):
                return True
            # scim-qt*
            if fnmatch(dirname, '/usr/lib*/qt*/plugins/inputmethods'):
                return True
            # gstreamer
            if fnmatch(dirname, '/usr/lib*/gstreamer-*'):
                return True
            # xine-lib
            if fnmatch(dirname, '/usr/lib*/xine/plugins/*'):
                return True
	    # kde/qt widget styles
	    if fnmatch(dirname, '/usr/lib*/qt*/plugins/styles/*'):
	        return True
	    if fnmatch(dirname, '/usr/lib*/kde*/plugins/styles/*'):
	        return True
        return False

class DevelMultilibMethod(RuntimeMultilibMethod):
    def __init__(self):
        self.name = 'devel'
    
    def select(self, po):
        blacklist = ['dmraid-devel', 'kdeutils-devel', 'mkinitrd-devel', 'java-1.5.0-gcj-devel', 'java-1.7.0-icedtea-devel', 'php-devel', 'java-1.6.0-openjdk-devel' ]
        whitelist = ['perl']
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
        if po.name.endswith('-devel'):
            return True
        return False

