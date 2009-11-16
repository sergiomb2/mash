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
import logging
import shutil
import sys


try:
    import koji
except:
    import brew as koji
import rpm
import urlgrabber
import time

import arch as masharch
import multilib
import metadata
import yum

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
        self._setupLogger()

    def _setupLogger(self):
        self.logger = logging.getLogger('mash')
        formatter = logging.Formatter('%(asctime)s %(name)s: %(message)s', '%Y-%m-%d %X')
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        console.setLevel(logging.INFO)
        self.logger.addHandler(console)
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

    def _makeMetadata(self, path, repocache, arch, comps = False, repoview = True, gofast = False, previous = None):
        md = metadata.Metadata(self.logger)
        md.set_ancient(self.config.make_ancient)
        md.set_cachedir(repocache)
        md.set_skipstat(gofast)
        md.set_database(self.config.use_sqlite)
        md.set_hash(self.config.hash)
        if comps and self.config.compsfile:
            md.set_comps(self.config.compsfile)
        d = os.path.join(self.config.rpm_path,"")
        if self.config.debuginfo_path.startswith(d):
            exclude = os.path.join(self.config.debuginfo_path.replace(d, ""), "*")
            md.set_excludes(exclude)
        if comps:
            if self.config.delta:
                paths = []
                if self.config.delta_dirs:
                    for dir in self.config.delta_dirs:
                        paths.append(dir % {'arch': arch })
                md.set_delta(paths)
        if previous:
            md.set_previous(previous)
        # Setup the distro tags
        if self.config.distro_tags:
            md.set_distro_tags(self.config.distro_tags)
        # Setup the content tags based on what we're making
        if arch == 'SRPMS':
            md.set_content_tags(['source'])
        elif path.endswith(self.config.debuginfo_path % {'arch': arch}):
            md.set_content_tags(['debuginfo-%s' % arch])
        else:
            md.set_content_tags(['binary-%s' % arch])
        md.run(path)
        self.logger.info("createrepo: finished %s" % (path,))
        if repoview and self.config.use_repoview:
            repoview_cmd = ["/usr/bin/repoview","-q", "--title",
                            self.config.repoviewtitle % { 'arch':arch }, "-u",
                            self.config.repoviewurl % { 'arch':arch }, path]
            self.logger.info("Running repoview for %s" % (path,))
            os.execv("/usr/bin/repoview", repoview_cmd)
        else:
            os._exit(0)

    def doCompose(self):
        def _matches(pkg, path):
            try:
                po = yum.packages.YumLocalPackage(self.rpmts, path)
                if po.name != pkg['name']:
                    return False
                if po.arch != pkg['arch']:
                    return False
                if po.version != pkg['version']:
                    return False
                if po.release != pkg['release']:
                    return False
                if pkg['epoch']:
                    if int(po.epoch) != pkg['epoch']:
                        return False
                elif po.epoch != '0':
                    return False

                if po.hdr.sprintf("%{PKGID}") != pkg['payloadhash']:
                    return False
                (err, (sigtype, sigdate, sigid)) = rpmUtils.miscutils.getSigInfo(po.hdr)
                if pkg['sigkey'] and pkg['sigkey'] != sigid[-8:]:
                    return False
                return True
            except:
                return False

        def _install(pkg, path):
              result = None
              filename = '%(name)s-%(version)s-%(release)s.%(arch)s.rpm' % pkg

              dst = os.path.join(path, filename)
              # Check cache for package
              if self.config.cachedir:
                  cachepath = os.path.join(self.config.cachedir, pkg['name'], filename)
                  if os.path.exists(cachepath) and _matches(pkg, cachepath):
                      result = cachepath
              if not result:
                  z = pkg.copy()
                  z['name'] = builds_hash[pkg['build_id']]['package_name']
                  z['version'] = builds_hash[pkg['build_id']]['version']
                  z['release'] = builds_hash[pkg['build_id']]['release']

                  # WARNING: this has improper knowledge of koji filesystem layout
                  srcurl = os.path.join(koji.pathinfo.build(z), koji.pathinfo.signed(pkg, pkg['sigkey']))
                  try:
                      os.mkdir(os.path.dirname(cachepath))
                  except:
                      pass
                  try:
                      result = urlgrabber.grabber.urlgrab(srcurl, cachepath)
                  except:
                      if self.config.strict_keys:
                          self.logger.error("ERROR: can't download %s from signed path %s" % (nevra(pkg), srcurl))
                          return 1
                      srcurl = os.path.join(koji.pathinfo.build(z), koji.pathinfo.rpm(pkg))
                      try:
                          result = urlgrabber.grabber.urlgrab(srcurl, cachepath)
                      except:
                          self.logger.error("ERROR: can't download %s from %s" % (nevra(pkg), srcurl))
                          return 1

              if result != dst:
                  try:
                      os.link(result, dst)
                  except:
                      shutil.copy2(result, dst)
              return 0

        def _write_files(list, path, repo_path, comps = False, repocache = None, arch = None):
            self.logger.info("Writing out files for %s..." % (path,))
            os.makedirs(path)
            
            pid = os.fork()
            if pid:
                return pid
            rc = 0
            for pkg in list:
                rc = rc + _install(pkg, path)

            if rc > 0:
                self.logger.info("Can't find all files for %s, aborting" %(path,))
                os._exit(1)
            previous_path = None
            if self.config.previous:
                prefix = os.path.join(self.config.outputdir, self.config.name, "")
                suffix = repo_path.replace(prefix, "")
                previous_path = os.path.join(self.config.previous, suffix, "repodata")
            self.logger.info("createrepo: starting %s..." % (path,))
            status = self._makeMetadata(repo_path, repocache, arch, comps, previous = previous_path)

        def _get_reference(pkg, builds_hash):
            result = None
            filename = '%(name)s-%(version)s-%(release)s.%(arch)s.rpm' % pkg
            if self.config.cachedir:
                cachepath = os.path.join(self.config.cachedir, pkg['name'], filename)
                if os.path.exists(cachepath) and _matches(pkg, cachepath):
                    result = cachepath

            if not result:
                if pkg['sigkey']:
                    path = os.path.join(koji.pathinfo.build(builds_hash[pkg['build_id']]), koji.pathinfo.signed(pkg, pkg['sigkey']))
                else:
                    path = os.path.join(koji.pathinfo.build(builds_hash[pkg['build_id']]), koji.pathinfo.rpm(pkg))
                try:
                    os.mkdir(os.path.dirname(cachepath))
                except:
                    pass
                try:
                    result = urlgrabber.grabber.urlgrab(path, cachepath)
                except:
                    if self.config.strict_keys and pkg['sigkey']:
                        self.logger.error("ERROR: can't download %s from signed path %s" % (nevra(pkg), path))
                    path = os.path.join(koji.pathinfo.build(builds_hash[pkg['build_id']]), koji.pathinfo.rpm(pkg))
                    try:
                        result = urlgrabber.grabber.urlgrab(path, cachepath)
                    except:
                        self.logger.error("ERROR: can't download %s from %s" % (nevra(pkg), path))
                        return None

            fd = open(result)
            return fd

        def has_any(l1, l2):
            if type(l1) not in (type(()), type([])):
                l1 = [l1]
            if type(l2) not in (type(()), type([])):
                l2 = [l2]
            for I in l2:
                if I in l1:
                    return 1
            return 0

        if self.config.cachedir and not os.path.exists(self.config.cachedir):
            os.makedirs(self.config.cachedir, 0755)
        # Get package list. This is an expensive operation.
        self.logger.info("Getting package lists for %s..." % (self.config.tag))
        
        (pkglist, buildlist) = self.session.listTaggedRPMS(self.config.tag, inherit = self.config.inherit, latest = True, rpmsigs = True)
        # filter by key
        biglist = PackageList(self.config)
        for pkg in pkglist:
            biglist.add(pkg)
        builds_hash = dict([(x['build_id'], x) for x in buildlist])
        koji.pathinfo.topdir = self.config.repodir
        self.rpmts = rpmUtils.transaction.initReadOnlyTransaction()
        
        self.logger.info("Sorting packages...")
        
        packages = {}
        debug = {}
        noarch = PackageList(self.config)
        source = PackageList(self.config)
        for arch in self.config.arches:
            packages[arch] = PackageList(self.config)
            debug[arch] = PackageList(self.config)
            
        # Sort into lots of buckets.
        for pkg in biglist.packages():
            arch = pkg['arch']
            if arch == 'noarch':
                # Stow it in a list for later
                noarch.add(pkg)
                continue

            if arch == 'src':
                source.add(pkg)
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

        src_hash = dict([(x['build_id'],x) for x in source.packages()])
        excludearch = dict([(x['build_id'],'') for x in source.packages()])
        exclusivearch = excludearch.copy()
        # Get excludearch/exclusivearch lists for noarch packages
        for pkg in noarch.packages():
            srcpkg = src_hash[pkg['build_id']]
            self.logger.debug("Checking %s for Exclude/ExclusiveArch" % (nevra(pkg),))
            fn = _get_reference(srcpkg, builds_hash)
            # if build has no source rpm, check the binary
            if fn == None:
                fn = _get_reference(pkg, builds_hash)
            try:
                hdr = koji.get_rpm_header(fn)
            except:
                self.logger.error("Couldn't read header from %s (%s)" % (nevra(pkg), fn))
                if fn:
                    fn.close()
                continue
            excludearch[pkg['build_id']] = hdr['EXCLUDEARCH']
            exclusivearch[pkg['build_id']] = hdr['EXCLUSIVEARCH']
            fn.close()

        for pkg in noarch.packages():
            for target_arch in self.config.arches:
                if (excludearch[pkg['build_id']] and has_any(masharch.compat[target_arch], excludearch[pkg['build_id']])) or \
                        (exclusivearch[pkg['build_id']] and not has_any(masharch.compat[target_arch], [arch for arch in exclusivearch[pkg['build_id']] if arch != 'noarch'])):
                    self.logger.info("Excluding %s.%s from %s due to EXCLUDEARCH/EXCLUSIVEARCH" % (pkg['name'], pkg['arch'], target_arch))
                    continue
                else:
                    if pkg['name'].find('-debuginfo') != -1:
                        debug[target_arch].add(pkg)
                    else:
                        packages[target_arch].add(pkg)

        self.logger.info("Checking signatures...")
        
        # Do some checking
        exit = 0
        for arch in self.config.arches:
            for pkg in packages[arch].packages() + debug[arch].packages():
                if pkg['sigkey'] == None:
                    pkg['sigkey'] = ''
                key = pkg['sigkey'].lower()
                if key not in self.config.keys:
                    if key == '':
                        key = 'no key'
                    self.logger.warning("WARNING: package %s is not signed with a preferred key (signed with %s)" % (nevra(pkg), key))
                    if self.config.strict_keys:
                        exit = 1
        if exit:
            sys.exit(1)
        
        # Make the trees
        outputdir = os.path.join(self.config.outputdir, self.config.name)
        shutil.rmtree(outputdir, ignore_errors = True)
        os.makedirs(outputdir)
        tmpdir = "%s/mash-%s/" % (self.config.workdir, self.config.name,)
        repocache = os.path.join(tmpdir,".createrepo-cache")
        shutil.rmtree(repocache, ignore_errors = True)
        os.makedirs(repocache)
        
        pids = []
        for arch in self.config.arches:
            path = os.path.join(outputdir, self.config.rpm_path % { 'arch':arch })
            repo_path = os.path.join(outputdir, self.config.repodata_path % { 'arch':arch })
            pid = _write_files(packages[arch].packages(), path, repo_path,
                               repocache = repocache, comps = True, arch = arch)
            pids.append(pid)
            
            if self.config.debuginfo:
                path = os.path.join(outputdir, self.config.debuginfo_path % { 'arch': arch })
                pid = _write_files(debug[arch].packages(), path, path,
                                   repocache = repocache, arch = arch)
                pids.append(pid)
                
            
        path = os.path.join(outputdir, self.config.source_path)
        pid = _write_files(source.packages(), path, path, repocache = repocache, arch = 'SRPMS')
        pids.append(pid)
        
        self.logger.info("Waiting for file copy and createrepo to finish...")
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
    
    def doDepSolveAndMultilib(self, arch, repocache):
        
        do_multi = self.config.multilib
        
        try:
            method = { 'base'    : multilib.MultilibMethod,
                       'devel'   : multilib.DevelMultilibMethod,
                       'file'    : multilib.FileMultilibMethod,
                       'kernel'  : multilib.KernelMultilibMethod,
                       'all'     : multilib.AllMultilibMethod,
                       'none'    : multilib.NoMultilibMethod,
                       'runtime' : multilib.RuntimeMultilibMethod}[self.config.multilib_method]()
        except KeyError:
            self.logger.error("Invalid multilib method %s" % (self.config.multilib_method,))
            do_multi = False
            return
        
        tmpdir = "%s/mash-%s/" % (self.config.workdir, self.config.name,)
        repocache = os.path.join(tmpdir,".createrepo-cache")
        pid = os.fork()
        if pid:
            return pid
                
        if arch not in masharch.biarch.keys():
            os._exit(0)
        else:
            self.logger.info("Resolving multilib for arch %s using method %s" % (arch, self.config.multilib_method))
        pkgdir = os.path.join(self.config.outputdir, self.config.name, self.config.rpm_path % {'arch':arch})
        repodir = os.path.join(self.config.outputdir, self.config.name, self.config.repodata_path % {'arch':arch})
        tmproot = os.path.join(tmpdir, "%s-%s.tmp" % (self.config.name, arch))
            
        yumbase = yum.YumBase()
        yumbase.verbose_logger.setLevel(logging.ERROR)
        archlist = masharch.compat[arch]
        transaction_arch = arch
        if do_multi:
            archlist = archlist + masharch.compat[masharch.biarch[arch]]
            best_compat = masharch.compat[masharch.biarch[arch]][0]
            if rpmUtils.arch.archDifference(best_compat, arch) > 0:
                transaction_arch = best_compat
        if hasattr(rpmUtils.arch, 'ArchStorage'):
            yumbase.preconf.arch = transaction_arch
        else:
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
        yumbase.doSackSetup(archlist = archlist, thisrepo='%s-%s' % (self.config.name, arch))
        yumbase.doSackFilelistPopulate()

        filelist = []
            
        for pkg in yumbase.pkgSack:
            pname = "%s-%s-%s.%s.rpm" % (pkg.name, pkg.version, pkg.release, pkg.arch)
            if not os.path.exists(os.path.join(pkgdir, pname)):
                self.logger.error("WARNING: Could not open %s" % (pname,))
                continue
            if pkg.arch in masharch.compat[arch]:
                yumbase.tsInfo.addInstall(pkg)
                filelist.append(pname)
            elif do_multi and method.select(pkg):
                yumbase.tsInfo.addInstall(pkg)
                self.logger.debug("Adding package %s for multilib" % (pkg,))
                filelist.append(pname)
        self.logger.info("Resolving depenencies for arch %s" % (arch,))
        (rc, errors) = yumbase.resolveDeps()
        if do_multi:
            for f in yumbase.tsInfo.getMembers():
                file = os.path.basename(f.po.localPkg())
                
                if file not in filelist:
                    self.logger.debug("added %s" % (file,))
                    filelist.append(file)
                    
            for pkg in os.listdir(pkgdir):
                if pkg.endswith('.rpm') and pkg not in filelist:
                    self.logger.debug("removing %s" % (pkg,))
                    os.unlink(os.path.join(pkgdir, pkg))
            
            shutil.rmtree(tmproot, ignore_errors = True)
            self.logger.info("Running createrepo on %s..." %(repodir))
            self._makeMetadata(repodir, repocache, arch, comps = True, repoview = False, gofast = True)

        shutil.rmtree(tmproot, ignore_errors = True)
        os._exit(0)
        
    def doMultilib(self):
        tmpdir = "%s/mash-%s/" % (self.config.workdir, self.config.name,)
        repocache = os.path.join(tmpdir,".createrepo-cache")
        pids = []
        for arch in self.config.arches:
        
            pid = self.doDepSolveAndMultilib(arch, repocache)
            pids.append(pid)

        self.logger.info("Waiting for depsolve and createrepo to finish...")
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
        self.logger.info("Depsolve and createrepo finished.")
        return rc
        
