#!/usr/bin/python -tt

class MultilibMethod():
    def __init__(self):
        self.name = 'none'
        
    def select(self, po):
        return False

class AllMultilibMethod(MultilibMethod):
    def __init__(self):
        self.name = 'all'
    
    def select(self, po):
        return True
    
class DevelMultilibMethod(MultilibMethod):
    def __init__(self):
        self.name = 'devel'
    
    def select(self, po):
        if po.name.endswith('-devel'):
            return True
        return False

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
        # haaaaaack. This is an example. Don't use this.
        self.libdirs = [ '/usr/lib', '/usr/lib64', '/lib', '/lib64',
                         '/usr/lib/mysql', '/usr/lib64/mysql', 
                         '/usr/lib/qt-3.3/lib', '/usr/lib64/qt-3.3/lib' ]
    
    def select(self, po):
        for file in po.filenames:
            (dirname, filename) = file.rsplit('/', 1)
            if dirname in self.libdirs and fnmatch(filename, '*.so.*'):
                return True
        return False

