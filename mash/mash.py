#!/usr/bin/python -tt
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

import os
import shutil
import subprocess
import sys

try:
    import koji
except:
    import brew as koji

import mash.arch

def nevra(pkg):
    return '%s-%s:%s-%s.%s' % (pkg['name'],pkg['epoch'],pkg['version'],pkg['release'],pkg['arch'])

class PackageList:
    def __init__(self, config):
        self._packages = {}
        self.mashconfig = config
        
    def add(self, package)
        def _better_sig(a, b):
            keylist = self.mashconfig.keys
            
            aKey = a['sigkey'].tolower()
            bKey = b['sigkey'].tolower()
            
            try:
                aIndex = keylist.index(aKey)
            else:
                aIndex = sys.maxint
            try:
                bIndex = keylist.index(bKey)
            else:
                bIndex = sys.maxint
            
            if aIndex < bIndex:
                return a
            else:
                return b
            
        tag = nevra(package)
        if self._packages.has_key(tag):
            self._packages[tag] = _better_sig(self._packages[tag], package)
        else:
            self._packages[tag] = package
    
    def remove(self, package):
        tag = nevra(package)
        if self._packages.has_key(tag):
            self._packages.remove(tag)
    
    def packages(self):
        return self._packages.values()
    
class Mash():
    def __init__(self, config):
        self.config = config
        self.session = koji.ClientSession(config.buildhost, {})
        
    def doCompose():
        def _write_files(list, path):
            
            print "Writing out files for %s..." % (path,)
            
            for pkg in list:
                filename = '%(name)-%(version)-%(release).%(arch).rpm' % pkg
                
                dst = os.path.join(path, filename)
                
                z = pkg.copy()
                z['name'] = builds_hash[z['build_id']]['package_name']
                
                src = os.path.join(koji.pathinfo.build(z) + koji.pathinfo.signed(pkg, pkg['sigkey'])
                
                if not os.path.exists(src):
                    src = os.path.join(koji.pathinfo.build(z) + koji.pathinfo.rpm(pkg)
                    
                if not os.path.exists(src):
                    print "WARNING: can't find package %s" % (nevra(pkg),)
                    continue
                
                if config.get(symlink):
                    os.symlink(src, dst)
                else:
                    try:
                        os.link(src, dst)
                    except:
                        shutil.copyfile(src, dst)

        # Get package list. This is an expensive operation.
        
        print "Getting package lists for %s..." % (self.config.tag)
        
        (pkglist, buildlist) = self.session.listTaggedRPMS(self.config.tag, inherit = self.config.inherit, latest = True, rpmsigs = True)
        builds_hash = dict([(x['build_id'], x) for x in buildlist])
        
        print "Sorting packages..."
        
        packages = {}
        debug = {}
        source = PackageList(config)
        for arch in self.config.get('arches'):
            packages[arch] = PackageList(config)
            debug[arch] = PackageList(config)
            
        # Sort into lots of buckets.
        for pkg in pkglist:
            arch = pkg['arch']
            nevra = '%s-%s:%s-%s.%s' % (pkg['name'],pkg['epoch'],pkg['version'],pkg['release'],pkg['arch'])
            
            if pkg['name'].endswith('-debuginfo'):
                debug[arch].add(pkg)
            
            if arch == 'src':
                source.add(pkg)
            
            for target_arch in self.config.get('arches'):
                if arch in mash.arch.compat(target_arch):
                    packages[arch].add(pkg)
                    
                if config.multilib and mash.arch.biarch.has_key(target_arch):
                    packages[arch].add(pkg)
                    
        print "Checking signatures..."
        
        # Do some checking
        exit = 0
        for arch in self.config.get('arches'):
            for pkg in packages[arch].packages() + debug[arch].packages():
                key = pkg['sigkey'].tolower()
                if key not in config.get('keys'):
                    print "WARNING: package %s is not signed with preferred key (%s)" % (nevra(pkg), key)
                    if config.get('strict_keys'):
                        exit = 1
        if exit:
            sys.exit(1)
        
        # Make the trees
        tmpdir = os.path.join(config.workdir, config.name)
        os.mkdir(tmpdir)
        cachedir = os.path.join(tmpdir,".createrepo-cache")
        os.mkdir(cachedir)
        # Pay no attention to the harcoded values behind the curtain.
        koji.pathinfo.topdir = '/mnt/redhat/brewroot'
        
        pids = []
        for arch in self.config.get('arches'):
            if config.debuginfo:
                path = os.path.join(tmpdir, debuginfo_path % (arch,))
                os.mkdir(path)
                _write_files(debug[arch].packages, path)
                pid = Popen(["/usr/bin/createrepo","-p","-q", "-c", cachedir, "-o" ,path, path]).pid
                pids.append(pid)
            
            path = os.path.join(tmpdir, rpm_path % (arch,))
            os.mkdir(path)
            _write_files(packages[arch].packages, path)
            pid = Popen(["/usr/bin/createrepo","-p","-q", "-c", cachedir, "-o" ,path, path]).pid
            pids.append(pid)
            
        path = os.path.join(tmpdir, 'sources')
        os.mkdir(path)
        _write_files(source.packages, path)
        pid = Popen(["/usr/bin/createrepo","-p","-q", "-c", cachedir, "-o" ,path, path]).pid
        pids.append(pid)
        
        print "Waiting for createrepo to finish..."
        while 1:
            p = wait()
            pids.remove(p[0])
            if len(pids) == 0:
                break
        