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
import sys


try:
    import koji
except:
    import brew as koji
import rpm
import createrepo
import urlgrabber

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

    def _makeMetadata(self, path, cachedir, arch, comps = False, repoview = True):
        conf = createrepo.MetaDataConfig()
        conf.cachedir = cachedir
        conf.update  = True
        conf.outputdir = path
        conf.directory = path
        conf.quiet = True
        if self.config.use_sqlite:
            conf.database = True
        if comps and self.config.compsfile:
           conf.groupfile = self.config.compsfile
        if self.config.debuginfo_path == os.path.join(self.config.rpm_path, 'debug'):
            conf.excludes.append("debug/*")
        repomatic = createrepo.MetaDataGenerator(conf)
        repomatic.doPkgMetadata()
        repomatic.doRepoMetadata()
        repomatic.doFinalMove()
        if repoview and self.config.use_repoview:
            repoview_cmd = ["/usr/bin/repoview","-q", "--title",
                            self.config.repoviewtitle % { 'arch':arch }, "-u",
                            self.config.repoviewurl % { 'arch':arch }, path]
            os.execv("/usr/bin/repoview", repoview_cmd)
        else:
            os._exit(0)

    def doCompose(self):
        def _write_files(list, path, repo_path, comps = False, cachedir = None, arch = None):
            
            print "Writing out files for %s..." % (path,)
            os.makedirs(path)
            
            pid = os.fork()
            if pid:
                return pid
            
            for pkg in list:
                filename = '%(name)s-%(version)s-%(release)s.%(arch)s.rpm' % pkg
                
                dst = os.path.join(path, filename)
                
                z = pkg.copy()
                z['name'] = builds_hash[pkg['build_id']]['package_name']
                z['version'] = builds_hash[pkg['build_id']]['version']
                z['release'] = builds_hash[pkg['build_id']]['release']
                
                # WARNING: this has improper knowledge of koji filesystem layout
                srcurl = os.path.join(koji.pathinfo.build(z), koji.pathinfo.signed(pkg, pkg['sigkey']))
                try:
                    result = urlgrabber.grabber.urlgrab(srcurl, dst)
                except:
                    srcurl = os.path.join(koji.pathinfo.build(z), koji.pathinfo.rpm(pkg))
                    try:
                        result = urlgrabber.grabber.urlgrab(srcurl, dst)
                    except:
                        print "WARNING: can't download %s from %s" % (nevra(pkg), srcurl)
                    continue
                if result != dst:
                    if self.config.symlink:
                        try:
                            os.symlink(result, dst)
                        except:
                            print "couldn't link %s to %s (%d %d)" % (result, dst, os.path.exists(result), os.path.exists(os.path.dirname(dst)))
                    else:
                        try:
                            os.link(result, dst)
                        except:
                            shutil.copyfile(result, dst)

            status = self._makeMetadata(repo_path, cachedir, arch, comps)

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
        koji.pathinfo.topdir = self.config.repodir
        
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
                source.add(pkg)
                path = os.path.join(koji.pathinfo.build(builds_hash[pkg['build_id']]), koji.pathinfo.rpm(pkg))
                fn = urlgrabber.grabber.urlopen(path)
                try:
                    fn.fileno = fn.fo.fp.fileno
                except:
                    pass
                try:
                    hdr = koji.get_rpm_header(fn)
                except:
                    print "Couldn't read header from %s, %s" % (path, fn)
                    continue
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

                # if excludearch is not set this build likely has no src.rpm
                # so set excludearch and exclusivearch from the binary
                if pkg['build_id'] not in excludearch:
                    path = os.path.join(koji.pathinfo.build(builds_hash[pkg['build_id']]), koji.pathinfo.rpm(pkg))
                    fn = urlgrabber.grabber.urlopen(path)
                    try:
                      fn.fileno = fn.fo.fp.fileno
                    except:
                      pass
                    try:
                        hdr = koji.get_rpm_header(fn)
                    except:
                        print "Couldn't read header from %s, %s" % (path, fn)
                        continue
                    excludearch[pkg['build_id']] = hdr['EXCLUDEARCH']
                    exclusivearch[pkg['build_id']] = hdr['EXCLUSIVEARCH']
                    fn.close()

                if (excludearch[pkg['build_id']] and has_any(masharch.compat[target_arch], excludearch[pkg['build_id']])) or \
                        (exclusivearch[pkg['build_id']] and not has_any(masharch.compat[target_arch], exclusivearch[pkg['build_id']])):
                    print "Excluding %s.%s from %s due to EXCLUDEARCH/EXCLUSIVEARCH" % (pkg['name'], pkg['arch'], target_arch)
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
                else:
                    z = pkg.copy()
                    z['name'] = builds_hash[pkg['build_id']]['package_name']
                    z['version'] = builds_hash[pkg['build_id']]['version']
                    z['release'] = builds_hash[pkg['build_id']]['release']
                    p = os.path.join(koji.pathinfo.build(z), koji.pathinfo.signed(pkg, pkg['sigkey']))
        if exit:
            sys.exit(1)
        
        # Make the trees
        outputdir = os.path.join(self.config.workdir, self.config.name)
        shutil.rmtree(outputdir, ignore_errors = True)
        os.makedirs(outputdir)
        tmpdir = "/tmp/mash-%s/" % (self.config.name,)
        cachedir = os.path.join(tmpdir,".createrepo-cache")
        shutil.rmtree(cachedir, ignore_errors = True)
        os.makedirs(cachedir)
        
        pids = []
        for arch in self.config.arches:
            path = os.path.join(outputdir, self.config.rpm_path % { 'arch':arch })
            repo_path = os.path.join(outputdir, self.config.repodata_path % { 'arch':arch })
            pid = _write_files(packages[arch].packages(), path, repo_path,
                               cachedir = cachedir, comps = True, arch = arch)
            pids.append(pid)
            
            if self.config.debuginfo:
                path = os.path.join(outputdir, self.config.debuginfo_path % { 'arch': arch })
                pid = _write_files(debug[arch].packages(), path, path,
                                   cachedir = cachedir, arch = arch)
                pids.append(pid)
                
            
        path = os.path.join(outputdir, self.config.source_path)
        pid = _write_files(source.packages(), path, path, cachedir = cachedir, arch = 'SRPMS')
        pids.append(pid)
        
        print "Waiting for createrepo to finish..."
        rc = 0
        while 1:
            try:
                (p, status) = os.wait()
            except:
                break
            pids.remove(p)
            if not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
                rc = 1
            if len(pids) == 0:
                break
        return rc
    
    def doDepSolveAndMultilib(self, arch, cachedir):
        
        do_multi = self.config.multilib
        
        try:
            method = { 'devel'   : multilib.DevelMultilibMethod,
                       'file'    : multilib.FileMultilibMethod,
                       'all'     : multilib.AllMultilibMethod,
                       'none'    : multilib.NoMultilibMethod,
                       'runtime' : multilib.RuntimeMultilibMethod}[self.config.multilib_method]()
        except KeyError:
            print "Invalid multilib method %s" % (self.config.multilib_method,)
            do_multi = False
            return
        
        tmpdir = "/tmp/mash-%s/" % (self.config.name,)
        cachedir = os.path.join(tmpdir,".createrepo-cache")
        pid = os.fork()
        if pid:
            return pid
        import yum
                
        if arch not in masharch.biarch.keys():
            os._exit(0)
        else:
            print "Resolving multilib for arch %s using method %s" % (arch, self.config.multilib_method)
        pkgdir = os.path.join(self.config.workdir, self.config.name, self.config.rpm_path % {'arch':arch})
        repodir = os.path.join(self.config.workdir, self.config.name, self.config.repodata_path % {'arch':arch})
        tmproot = os.path.join(tmpdir, "%s-%s.tmp" % (self.config.name, arch))
            
        yumbase = yum.YumBase()
        archlist = masharch.compat[arch]
        transaction_arch = arch
        if do_multi:
            archlist = archlist + masharch.compat[masharch.biarch[arch]]
            best_compat = masharch.compat[masharch.biarch[arch]][0]
            if rpmUtils.arch.archDifference(best_compat, arch) > 0:
                transaction_arch = best_compat
        rpmUtils.arch.canonArch = transaction_arch
            
        yconfig = """
[main]
debuglevel=2
pkgpolicy=newest
exactarch=1
gpgcheck=0
reposdir=/dev/null
cachedir=/yumcache
installroot=%s
logfile=/yum.log

[%s-%s]
name=%s
baseurl=file://%s
enabled=1

""" % (tmproot, self.config.name, arch, self.config.name, repodir)
        shutil.rmtree(tmproot, ignore_errors = True)
        os.makedirs(os.path.join(tmproot,"yumcache"))
        os.makedirs(os.path.join(tmproot,'var/lib/rpm'))
        yconfig_path = os.path.join(tmproot, 'yum.conf-%s-%s' % (self.config.name, arch))
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
        yumbase.doSackSetup(archlist = archlist, thisrepo=self.config.name)
        yumbase.doSackFilelistPopulate()

        filelist = []
            
        for pkg in yumbase.pkgSack:
            pname = "%s-%s-%s.%s.rpm" % (pkg.name, pkg.version, pkg.release, pkg.arch)
            if not os.path.exists(os.path.join(pkgdir, pname)):
                print "WARNING: Could not open %s" % (pname,)
                continue
            if pkg.arch in masharch.compat[arch]:
                yumbase.tsInfo.addInstall(pkg)
                filelist.append(pname)
            elif do_multi and method.select(pkg):
                yumbase.tsInfo.addInstall(pkg)
                print "Adding package %s for multilib" % (pkg,)
                filelist.append(pname)

        (rc, errors) = yumbase.resolveDeps()
        if errors:
            pass
            #print "Unresolved dependencies on %s:" % (arch,)
            #for error in errors:
            #    print error
        if do_multi:
            for f in yumbase.tsInfo.getMembers():
                file = os.path.basename(f.po.localPkg())
                
                if file not in filelist:
                    print "added %s" % (file,)
                    filelist.append(file)
                    
            for pkg in os.listdir(pkgdir):
                if pkg.endswith('.rpm') and pkg not in filelist:
                    print "removing %s" % (pkg,)
                    os.unlink(os.path.join(pkgdir, pkg))
            
            shutil.rmtree(tmproot, ignore_errors = True)
            print "Running createrepo on %s..." %(repodir),
            self._makeMetadata(repodir, cachedir, arch, comps = True, repoview = False)

        shutil.rmtree(tmproot, ignore_errors = True)
        os._exit(0)
        
    def doMultilib(self):
        tmpdir = "/tmp/mash-%s/" % (self.config.name,)
        cachedir = os.path.join(tmpdir,".createrepo-cache")
        pids = []
        for arch in self.config.arches:
        
            pid = self.doDepSolveAndMultilib(arch, cachedir)
            pids.append(pid)

        print "Waiting for depsolve and createrepo to finish..."
        rc = 0
        while 1:
            try:
                (p, status) = os.wait()
            except:
                break
            pids.remove(p)
            if not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
                rc = 1
            if len(pids) == 0:
                break
        shutil.rmtree(tmpdir, ignore_errors = True)
        return rc
        
