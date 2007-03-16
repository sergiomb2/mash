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
import rpm
import yum

import arch as masharch
import multilib

import rpmUtils.arch

def nevra(pkg):
    return '%s-%s:%s-%s.%s' % (pkg['name'],pkg['epoch'],pkg['version'],pkg['release'],pkg['arch'])

class PackageList:
    def __init__(self, config):
        self._packages = {}
        self.mashconfig = config
        
    def add(self, package):
        def _better_sig(a, b):
            keylist = self.mashconfig.keys
            
            aKey = a['sigkey'].lower()
            bKey = b['sigkey'].lower()
            
            try:
                aIndex = keylist.index(aKey)
            except:
                aIndex = sys.maxint
            try:
                bIndex = keylist.index(bKey)
            except:
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
        
    def doCompose(self):
        def _write_files(list, path):
            
            print "Writing out files for %s..." % (path,)
            
            for pkg in list:
                filename = '%(name)s-%(version)s-%(release)s.%(arch)s.rpm' % pkg
                
                dst = os.path.join(path, filename)
                
                z = pkg.copy()
                z['name'] = builds_hash[z['build_id']]['package_name']
                
                src = os.path.join(koji.pathinfo.build(z), koji.pathinfo.signed(pkg, pkg['sigkey']))
                
                if not os.path.exists(src):
                    src = os.path.join(koji.pathinfo.build(z), koji.pathinfo.rpm(pkg))
                    
                if not os.path.exists(src):
                    print "WARNING: can't find package %s as %s" % (nevra(pkg), src)
                    continue
                
                if self.config.symlink:
                    os.symlink(src, dst)
                else:
                    try:
                        os.link(src, dst)
                    except:
                        shutil.copyfile(src, dst)

        # Get package list. This is an expensive operation.
        
        print "Getting package lists for %s..." % (self.config.tag)
        
        (pkglist, buildlist) = self.session.listTaggedRPMS(self.config.tag, inherit = self.config.inherit, latest = True, package = 'glibc', rpmsigs = True)
        builds_hash = dict([(x['build_id'], x) for x in buildlist])
        
        print "Sorting packages..."
        
        packages = {}
        debug = {}
        source = PackageList(self.config)
        for arch in self.config.arches:
            packages[arch] = PackageList(self.config)
            debug[arch] = PackageList(self.config)
            
        # Sort into lots of buckets.
        for pkg in pkglist:
            arch = pkg['arch']
            
            if pkg['name'].endswith('-debuginfo') and debug.has_key(arch):
                debug[arch].add(pkg)
                continue
            
            if arch == 'src':
                source.add(pkg)
                continue
            
            for target_arch in self.config.arches:
                if not masharch.compat.has_key(arch):
                    masharch.compat[arch] = ( arch, 'noarch' )
                
                if arch in masharch.compat[target_arch]:
                    packages[target_arch].add(pkg)
                    
                if self.config.multilib and masharch.biarch.has_key(target_arch):
                    if arch in masharch.compat[masharch.biarch[target_arch]]:
                        packages[target_arch].add(pkg)
                    
        print "Checking signatures..."
        
        # Do some checking
        exit = 0
        for arch in self.config.arches:
            for pkg in packages[arch].packages() + debug[arch].packages():
                key = pkg['sigkey'].lower()
                if key not in self.config.keys:
                    print "WARNING: package %s is not signed with a preferred key (signed with %s)" % (nevra(pkg), key)
                    if self.config.strict_keys:
                        exit = 1
        if exit:
            sys.exit(1)
        
        # Make the trees
        tmpdir = os.path.join(self.config.workdir, self.config.name)
        shutil.rmtree(tmpdir, ignore_errors = True)
        os.makedirs(tmpdir)
        cachedir = os.path.join(tmpdir,".createrepo-cache")
        os.makedirs(cachedir)
        # Pay no attention to the harcoded values behind the curtain.
        koji.pathinfo.topdir = '/mnt/redhat/brewroot'
        
        pids = []
        for arch in self.config.arches:
            if self.config.debuginfo:
                path = os.path.join(tmpdir, self.config.debuginfo_path % { 'arch': arch })
                os.makedirs(path)
                _write_files(debug[arch].packages(), path)
                pid = subprocess.Popen(["/usr/bin/createrepo","-p","-q", "-c", cachedir, "-o" ,path, path]).pid
                pids.append(pid)
            
            path = os.path.join(tmpdir, self.config.rpm_path % { 'arch':arch })
            os.makedirs(path)
            _write_files(packages[arch].packages(), path)
            pid = subprocess.Popen(["/usr/bin/createrepo","-p","-q", "-c", cachedir, "-o" ,path, path]).pid
            pids.append(pid)
            
        path = os.path.join(tmpdir, 'sources')
        os.makedirs(path)
        _write_files(source.packages(), path)
        pid = subprocess.Popen(["/usr/bin/createrepo","-p","-q", "-c", cachedir, "-o" ,path, path]).pid
        pids.append(pid)
        
        print "Waiting for createrepo to finish..."
        while 1:
            try:
                p = os.wait()
            except:
                break
            pids.remove(p[0])
            if len(pids) == 0:
                break
    
    def doMultilib(self):
        
        if not self.config.multilib:
            return
        
        try:
            method = { 'devel'   : multilib.DevelMultilibMethod,
                       'file'    : multilib.FileMultilibMethod,
                       'all'     : multilib.AllMultilibMethod,
                       'none'    : multilib.MultilibMethod,
                       'runtime' : multilib.RuntimeMultilibMethod}[self.config.multilib_method]()
        except KeyError:
            print "Invalid multilib method %s" % (self.config.multilib_method,)
            return
        
        for arch in self.config.arches:
            
            if arch not in masharch.biarch.keys():
                continue
            
            print "Resolving multilib for arch %s using method %s" % (arch, self.config.multilib_method)
            repodir = os.path.join(self.config.workdir, self.config.name, self.config.rpm_path % {'arch':arch})
            cachedir = os.path.join(self.config.workdir, "yumcache")
            rpmdb = os.path.join(self.config.workdir, "%s-%s.rpm" % (self.config.name, arch))
            
            yumbase = yum.YumBase()
            rpmUtils.arch.canonArch = arch
            
            yconfig = """
[main]
debuglevel=2
pkgpolicy=newest
exactarch=1
gpgcheck=0
reposdir=/dev/null
cachedir=%s
installroot=%s

[%s]
name=%s
baseurl=file://%s
enabled=1
cache=1
""" % (cachedir, rpmdb, self.config.name, self.config.name, repodir)
            shutil.rmtree(cachedir)
            os.makedirs(cachedir)
            shutil.rmtree(os.path.join(rpmdb), ignore_errors = True)
            os.makedirs(os.path.join(rpmdb,'var/lib/rpm'))
            yconfig_path = os.path.join(self.config.workdir, 'yum.conf-%s-%s' % (self.config.name, arch))
            f = open(yconfig_path, 'w')
            f.write(yconfig)
            f.close()
            yumbase.doConfigSetup(fn=yconfig_path)
            yumbase.doRepoSetup()
            yumbase.doTsSetup()
            yumbase.doRpmDBSetup()
            # Nggh.
            yumbase.ts.pushVSFlags((rpm._RPMVSF_NOSIGNATURES|rpm._RPMVSF_NODIGESTS))
            archlist = masharch.compat[arch] + masharch.compat[masharch.biarch[arch]]
            yumbase.doSackSetup(archlist = archlist, thisrepo=self.config.name)
            
            yumbase.doSackFilelistPopulate()

            filelist = []
            
            for pkg in os.listdir(repodir):
                try:
                    ypkg = yum.YumLocalPackage(ts = yumbase.ts, filename = os.path.join(repodir, pkg))
                    if ypkg.arch in masharch.compat[arch]:
                        yumbase.tsInfo.addInstall(ypkg)
                        filelist.append(pkg)
                    elif method.select(ypkg):
                        yumbase.tsInfo.addInstall(ypkg)
                        filelist.append(pkg)
                except:
                    if pkg.endswith('.rpm'):
                        print "WARNING: Could not open %s" % (pkg,)
                    continue
                
            yumbase.resolveDeps()
            for f in yumbase.tsInfo.getMembers():
                file = os.path.basename(f.po.localPkg())
                
                if file not in filelist:
                    print "added %s" % (file,)

            # at this point we remove the unneeded biarch packages and run creatrepo