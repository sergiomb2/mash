#!/usr/bin/python -tt

class MultilibMethod():
    def __init__(self):
        self.name = 'base'
        self.prefer_64 = [ 'kernel', 'gdb', 'frysk' ]
    def select(self, po):
        if po.arch.find('64') != -1 and po.name in self.prefer_64:
            return True
        return False

class NoMultilibMethod():
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
        self.libdirs = [ '/usr/lib', '/usr/lib64', '/lib', '/lib64' ]
    
    def select(self, po):
        if MultlibMethod.select(po):
            return True
        for file in po.filenames:
            (dirname, filename) = file.rsplit('/', 1)
            # libraries in standard dirs
            if dirname in self.libdirs and fnmatch(filename, '*.so.*'):
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
        if RuntimeMultilibMethod.select(po):
            return True
        if po.name.endswith('-devel'):
            return True
        return False

