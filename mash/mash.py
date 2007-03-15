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

try:
    import koji
except:
    import brew as koji

import mash.arch
    
class Mash():
    def __init__(self, config):
        self.config = config
        self.session = koji.ClientSession(config.get('buildhost'), {})
        
    def doCompose():
        
        def betterSig(a, b):
            keylist = config.get('keys')
            
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
        
        # Get package list. This is an expensive operation.
        (pkglist, buildlist) = self.session.listTaggedRPMS(self.config.tag, inherit = self.config.inherit, latest = True, rpmsigs = True)
        builds_hash = dict([(x['build_id'], x) for x in buildlist])
        
        packages = {}
        debug = {}
        source = {}
        for arch in self.config.get('arches'):
            packages[arch] = {}
            debug[arch] = {}
            
        # Sort into lots of buckets.
        for pkg in pkglist:
            arch = pkg['arch']
            nevra = '%s-%s:%s-%s.%s' % (pkg['name'],pkg['epoch'],pkg['version'],pkg['release'],pkg['arch'])
            
            if pkg['name'].endswith('-debuginfo'):
                if not debug[arch].has_key(nevra):
                    debug[arch][nevra] = pkg
                else:
                    debug[arch][nevra] = betterSig(debug[arch][nevra], pkg)
                continue
            
            if arch == 'src':
                if not source.has_key(nevra):
                    source[nevra] = pkg
                else:
                    source[nevra] = betterSig(source[nevra], pkg)
                continue
            
            for target_arch in self.config.get('arches'):
                if arch in mash.arch.compat(target_arch):
                    if not packages[arch].has_key(nevra):
                        packages[arch][nevra] = pkg
                    else:
                        packages[arch][nevra] = betterSig(packages[arch][nevra], pkg)
                
                if config.multilib and mash.arch.biarch.has_key(target_arch):
                    if arch in mash.arch.compat[mash.arch.biarch[target_arch]]:
                        if not packages[arch].has_key(nevra):
                            packages[arch][nevra] = pkg
                        else:
                            packages[arch][nevra] = betterSig(packages[arch][nevra], pkg)
        
        # Do some checking
        exit = 0
        for arch in self.config.get('arches'):
            for pkg in packages[arch].values() + debug[arch].values():
                key = pkg['sigkey'].tolower()
                nevra = '%s-%s:%s-%s.%s' % (pkg['name'],pkg['epoch'],pkg['version'],pkg['release'],pkg['arch'])
                if key not in config.get('keys'):
                    print "WARNING: package %s is not signed with preferred key (%s)" % (nevra, key)
                    if config.get('strict_keys'):
                        exit = 1
        if exit:
            sys.exit(1)
        
        # Make the trees
        tmpdir = config.get('workdir')
        os.mkdir(tmpdir)
        koji.pathinfo.topdir = '/mnt/redhat/brewroot'
        for arch in self.config.get('arches'):
            os.mkdir(os.path.join(tmpdir,arch,product_path))
            
            os.mkdir(os.path.join(tmpdir,arch,debug_path))
            for package in debug[arch].values():
                filename = '%(name)-%(version)-%(release).%(arch).rpm' % package
                
                z = package.copy()
                z['name'] = builds_hash[z['build_id']]['package_name']
                
                path = os.path.join(brew.pathinfo.build(z) + brew.pathinfo.signed(package, package['sigkey'])
                
                if not os.path.exists(path):
                    path = os.path.join(brew.pathinfo.build(z) + brew.pathinfo.rpm(package)
                    
                if not os.path.exists(path):
                    print "WARNING: can't find package %s" % (nevra(package),)
                    continue
                
                if config.get(symlink):
                    os.symlink(path, os.path.join(tmpdir,arch,debug_path,filename))
                else:
                    try:
                        os.link(path, os.path.join(tmpdir, arch, debug_path, filename))
                    except:
                        shutil.copyfile(path, os.path.join(tmpdir, arch, debug_path, filename))

            