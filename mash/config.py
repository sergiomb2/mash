# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import glob
import string

from ConfigParser import RawConfigParser

from yum import config

class MashConfig(config.BaseConfig):
    rpm_path = config.Option('Mash')
    repodata_path = config.Option()
    source_path = config.Option('source/SRPMS')
    debuginfo = config.BoolOption(True)
    debuginfo_path = config.Option('%(arch)s/debug')
    multilib = config.BoolOption(True)
    multilib_method = config.Option('devel')
    multilib_file = config.Option()
    arches = config.ListOption()
    keys = config.ListOption()
    configdir = config.Option('/etc/mash')
    strict_keys = config.BoolOption(False)
    workdir = config.Option('/var/tmp/mash')
    outputdir = config.Option('/var/tmp/mash')
    cachedir = config.Option('/var/cache/mash')
    buildhost = config.Option()
    repodir = config.Option('/mnt/koji')
    compsfile = config.Option()
    use_sqlite = config.BoolOption(True)
    use_repoview = config.BoolOption(False)
    hash = config.Option('sha256')
    repoviewurl = config.Option('http://localhost/%(arch)s')
    repoviewtitle = config.Option('"Mash - %(arch)s"')
    delta = config.BoolOption(False)
    delta_dirs = config.ListOption()
    make_ancient = config.BoolOption(False)
    latest = config.BoolOption(True)
    distro_tags = config.Option()
    content_tags = config.ListOption()
    prefer_ppc64 = config.BoolOption(False)
    distros = []
    
class MashDistroConfig(config.BaseConfig):
    name = config.Option()
    rpm_path = config.Inherit(MashConfig.rpm_path)
    repodata_path = config.Inherit(MashConfig.repodata_path)
    source = config.BoolOption(True)
    source_path = config.Inherit(MashConfig.source_path)
    debuginfo = config.Inherit(MashConfig.debuginfo)
    debuginfo_path = config.Inherit(MashConfig.debuginfo_path)
    multilib = config.Inherit(MashConfig.multilib)
    multilib_method = config.Inherit(MashConfig.multilib_method)
    multilib_file = config.Inherit(MashConfig.multilib_file)
    arches = config.Inherit(MashConfig.arches)
    tag = config.Option()
    inherit = config.BoolOption(True)
    keys = config.Inherit(MashConfig.keys)
    configdir = config.Inherit(MashConfig.configdir)
    strict_keys = config.Inherit(MashConfig.strict_keys)
    buildhost = config.Inherit(MashConfig.buildhost)
    repodir = config.Inherit(MashConfig.repodir)
    workdir = config.Inherit(MashConfig.workdir)
    outputdir = config.Inherit(MashConfig.outputdir)
    output_subdir = config.Option()
    cachedir = config.Inherit(MashConfig.cachedir)
    compsfile = config.Inherit(MashConfig.compsfile)
    use_sqlite = config.Inherit(MashConfig.use_sqlite)
    hash = config.Inherit(MashConfig.hash)
    use_repoview = config.Inherit(MashConfig.use_repoview)
    repoviewurl = config.Inherit(MashConfig.repoviewurl)
    repoviewtitle = config.Inherit(MashConfig.repoviewtitle)
    delta = config.Inherit(MashConfig.delta)
    delta_dirs = config.Inherit(MashConfig.delta_dirs)
    make_ancient = config.Inherit(MashConfig.make_ancient)
    latest = config.Inherit(MashConfig.latest)
    distro_tags = config.Inherit(MashConfig.distro_tags)
    content_tags = config.Inherit(MashConfig.content_tags)
    prefer_ppc64 = config.Inherit(MashConfig.prefer_ppc64)
    hash_packages = config.BoolOption(False)
    parent_repos = config.ListOption()
    previous = None

    def fixup(self, sect):
        if not self.name:
            self.name = sect
        if not self.repodata_path:
            self.repodata_path = os.path.dirname(self.rpm_path)
        if not self.output_subdir:
            self.output_subdir = sect
        self.keys = map(string.lower, self.keys)
        if self.multilib_file and self.multilib_file[0] != '/':
            self.multilib_file = os.path.join(self.configdir, self.multilib_file)
        if len(self.keys) == 0:
            self.keys = ['']

def readMainConfig(conf):
    config = MashConfig()
    parser = RawConfigParser()
    parser.read(conf)
    config.populate(parser, 'defaults')
    config.parser = parser
    config.keys = map(string.lower, config.keys)
    if len(config.keys) == 0:
        config.keys = ['']
    
    for section in config.parser.sections():
        if section == 'defaults':
            continue
        
        thisdistro = MashDistroConfig()
        thisdistro.populate(parser, section)
        thisdistro.fixup(section)
        config.distros.append(thisdistro)
    
    if os.path.isdir(config.configdir):
        for file in glob.glob('%s/*.mash' % config.configdir):
            parser = RawConfigParser()
            parser.read(file)
            for sect in parser.sections():
                thisdistro = MashDistroConfig()
                thisdistro.populate(parser, sect, config)
                thisdistro.fixup(sect)
                config.distros.append(thisdistro)
    return config

