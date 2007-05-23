
from fnmatch import fnmatch

class MultilibMethod:
    def __init__(self):
        self.name = 'base'
    def select(self, po):
        prefer_64 = [ 'gdb', 'frysk', 'systemtap', 'systemtap-runtime', 'ltrace', 'strace', 'valgrind']
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
            
class RuntimeMultilibMethod(MultilibMethod):
    def __init__(self):
        self.name = 'runtime'
    
    def select(self, po):
        libdirs = [ '/usr/lib', '/usr/lib64', '/lib', '/lib64' ]
        whitelist = ['scim-bridge-gtk', 'scim-qtimm', 'redhat-artwork', 'gtk2-engines', 'libgnat', 'wine', 'wine-arts' ]
        if po.name in whitelist:
            return True
        if MultilibMethod.select(self,po):
            return True
        for file in po.returnFileEntries():
            (dirname, filename) = file.rsplit('/', 1)
            # libraries in standard dirs
            if dirname in libdirs and fnmatch(filename, '*.so.*'):
                return True
            # pam
            if dirname in [ '/lib/security', '/lib64/security' ]:
                return True
            # nss
            if dirname in [ '/lib', '/lib64' ] and filename.startswith('libnss_'):
                return True
            # mysql, qt, etc.
            if dirname == '/etc/ld.so.conf.d' and filename.endswith('.conf'):
                return True
        return False

class DevelMultilibMethod(RuntimeMultilibMethod):
    def __init__(self):
        self.name = 'devel'
    
    def select(self, po):
        blacklist = ['dmraid-devel', 'kdeutils-devel', 'mkinitrd-devel', 'java-1.5.0-gcj-devel']
        whitelist = ['perl']
        if po.name in blacklist:
            return False
        if po.name.startswith('kernel'):
            for (p_name, p_flag, (p_e, p_v, p_r)) in po.provides:
                if p_name == 'kernel-devel':
                    return False
        if po.name in whitelist:
            return True
        if RuntimeMultilibMethod.select(self,po):
            return True
        if po.name.endswith('-devel'):
            return True
        return False

