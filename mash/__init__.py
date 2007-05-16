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
    
class Mash:
    def __init__(self, config):
        self.config = config
        self.session = koji.ClientSession(config.buildhost, {})

    def _runCreateRepo(self, path, cachedir, comps = False, background = True):
        command = ["/usr/bin/createrepo","-p","-q", "-c", cachedir, "-o" ,path]
        if comps and self.config.compsfile:
            command = command + [ "-g", self.config.compsfile ]
        command = command + [ path ]
        pid = subprocess.Popen(command).pid
        if not background:
            os.waitpid(pid)
        return pid

    def doCompose(self):
        def _write_files(list, path):
            
            print "Writing out files for %s..." % (path,)
            
            for pkg in list:
                filename = '%(name)s-%(version)s-%(release)s.%(arch)s.rpm' % pkg
                
                dst = os.path.join(path, filename)
                
                z = pkg.copy()
                z['name'] = builds_hash[pkg['build_id']]['package_name']
                z['version'] = builds_hash[pkg['build_id']]['version']
                z['release'] = builds_hash[pkg['build_id']]['release']
                
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

        def has_any(l1, l2):
            if type(l1) not in (type(()), type([])):
                l1 = [l1]
            if type(l2) not in (type(()), type([])):
                l2 = [l2]
            for I in l2:
                if I in l1:
                    return 1
            return 0
        
        # Get package list. This is an expensive operation.
        
        print "Getting package lists for %s..." % (self.config.tag)
        
        (pkglist, buildlist) = self.session.listTaggedRPMS(self.config.tag, inherit = self.config.inherit, latest = True, rpmsigs = True)
        builds_hash = dict([(x['build_id'], x) for x in buildlist])
        
        print "Sorting packages..."
        
        packages = {}
        debug = {}
        excludearch = {}
        exclusivearch = {}
        noarch = []
        source = PackageList(self.config)
        for arch in self.config.arches:
            packages[arch] = PackageList(self.config)
            debug[arch] = PackageList(self.config)
            
        # Sort into lots of buckets.
        for pkg in pkglist:
            arch = pkg['arch']
            if arch == 'noarch':
                # Stow it in a list for later
                noarch.append(pkg)
                continue

            if arch == 'src':
                path = os.path.join(koji.pathinfo.build(builds_hash[pkg['build_id']]), koji.pathinfo.rpm(pkg))
                fn = open(path, 'r')
                hdr = koji.get_rpm_header(fn)
                source.add(pkg)
                excludearch[pkg['build_id']] = hdr['EXCLUDEARCH']
                exclusivearch[pkg['build_id']] = hdr['EXCLUSIVEARCH']
                fn.close()
                continue
             
            if pkg['name'].find('-debuginfo') != -1:
                for target_arch in self.config.arches:
                    if arch in masharch.compat[target_arch]:
                        debug[target_arch].add(pkg)
                continue
            
            for target_arch in self.config.arches:
                if not masharch.compat.has_key(arch):
                    masharch.compat[arch] = ( arch, 'noarch' )
                
                if arch in masharch.compat[target_arch]:
                    packages[target_arch].add(pkg)
                    
                if self.config.multilib and masharch.biarch.has_key(target_arch):
                    if arch in masharch.compat[masharch.biarch[target_arch]]:
                        packages[target_arch].add(pkg)
                    
        # now deal with noarch
        for pkg in noarch:
            for target_arch in self.config.arches:
                if (excludearch[pkg['build_id']] and has_any(masharch.compat[target_arch], excludearch[pkg['build_id']])) or \
                        (exclusivearch[pkg['build_id']] and not has_any(masharch.compat[target_arch], exclusivearch[pkg['build_id']])):
                    print "Excluding %s.%s from %s due to EXCLUDEARCH/EXCLUSIVEARCH" % (pkg['name'], pkg['arch'], arch)
                    continue
                else:
                    packages[target_arch].add(pkg)

        print "Checking signatures..."
        
        # Do some checking
        exit = 0
        for arch in self.config.arches:
            for pkg in packages[arch].packages() + debug[arch].packages():
                key = pkg['sigkey'].lower()
                if key not in self.config.keys:
                    if key == '':
                        key = 'no key'
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
        koji.pathinfo.topdir = self.config.repodir
        
        pids = []
        for arch in self.config.arches:
            if self.config.debuginfo:
                path = os.path.join(tmpdir, self.config.debuginfo_path % { 'arch': arch })
                os.makedirs(path)
                _write_files(debug[arch].packages(), path)
                pid = self._runCreateRepo(path, cachedir)
                pids.append(pid)
            
            path = os.path.join(tmpdir, self.config.rpm_path % { 'arch':arch })
            os.makedirs(path)
            _write_files(packages[arch].packages(), path)
            pid = self._runCreateRepo(os.path.dirname(path), cachedir, comps = True)
            pids.append(pid)
            
        path = os.path.join(tmpdir, 'source', 'SRPMS')
        os.makedirs(path)
        _write_files(source.packages(), path)
        pid = self._runCreateRepo(path, cachedir)
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
                       'none'    : multilib.NoMultilibMethod,
                       'runtime' : multilib.RuntimeMultilibMethod}[self.config.multilib_method]()
        except KeyError:
            print "Invalid multilib method %s" % (self.config.multilib_method,)
            return
        
        cachedir = os.path.join(self.config.workdir, self.config.name, ".createrepo-cache")
        pids = []
        for arch in self.config.arches:
            
            if arch not in masharch.biarch.keys():
                continue
            
            print "Resolving multilib for arch %s using method %s" % (arch, self.config.multilib_method)
            pkgdir = os.path.join(self.config.workdir, self.config.name, self.config.rpm_path % {'arch':arch})
            repodir = os.path.dirname(pkgdir)
            tmpdir = os.path.join(self.config.workdir, "%s-%s.tmp" % (self.config.name, arch))
            yumcachedir = os.path.join(tmpdir, "yumcache")
            
            yumbase = yum.YumBase()
            rpmUtils.arch.canonArch = arch
            
            yconfig = """
[main]
debuglevel=3
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
""" % (yumcachedir, tmpdir, self.config.name, self.config.name, repodir)
            shutil.rmtree(tmpdir, ignore_errors = True)
            os.makedirs(yumcachedir)
            os.makedirs(os.path.join(tmpdir,'var/lib/rpm'))
            yconfig_path = os.path.join(tmpdir, 'yum.conf-%s-%s' % (self.config.name, arch))
            f = open(yconfig_path, 'w')
            f.write(yconfig)
            f.close()
            yumbase.doConfigSetup(fn=yconfig_path)
            yumbase.conf.cache = 0
            yumbase.doRepoSetup()
            yumbase.doTsSetup()
            yumbase.doRpmDBSetup()
            # Nggh.
            yumbase.ts.pushVSFlags((rpm._RPMVSF_NOSIGNATURES|rpm._RPMVSF_NODIGESTS))
            archlist = masharch.compat[arch] + masharch.compat[masharch.biarch[arch]]
            yumbase.doSackSetup(archlist = archlist, thisrepo=self.config.name)
            
            yumbase.doSackFilelistPopulate()

            filelist = []
            
            for pkg in os.listdir(pkgdir):
                if not pkg.endswith('.rpm'):
                    continue
                try:
                    ypkg = yum.YumLocalPackage(ts = yumbase.ts, filename = os.path.join(pkgdir, pkg))
                    if ypkg.arch in masharch.compat[arch]:
                        yumbase.tsInfo.addInstall(ypkg)
                        filelist.append(pkg)
                    elif method.select(ypkg):
                        yumbase.tsInfo.addInstall(ypkg)
                        print "Adding package %s for multlib" %  (pkg,)
                        filelist.append(pkg)
                except:
                    print "WARNING: Could not open %s" % (pkg,)
                
            yumbase.resolveDeps()
            for f in yumbase.tsInfo.getMembers():
                file = os.path.basename(f.po.localPkg())
                
                if file not in filelist:
                    print "added %s" % (file,)
                    filelist.append(file)
                    
            for pkg in os.listdir(pkgdir):
                if pkg.endswith('.rpm') and pkg not in filelist:
                    print "removing %s" % (pkg,)
                    os.unlink(os.path.join(pkgdir, pkg))
            
            pid = self._runCreateRepo(repodir, cachedir, comps = True)
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
        
        shutil.rmtree(tmpdir, ignore_errors = True)
        shutil.rmtree(cachedir, ignore_errors = True)
        
