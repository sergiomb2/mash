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
    distro_tags = config.ListOption()
    content_tags = config.ListOption()
    distros = []
    
class MashDistroConfig(config.BaseConfig):
    name = config.Option()
    rpm_path = config.Inherit(MashConfig.rpm_path)
    repodata_path = config.Inherit(MashConfig.repodata_path)
    source_path = config.Inherit(MashConfig.source_path)
    debuginfo = config.Inherit(MashConfig.debuginfo)
    debuginfo_path = config.Inherit(MashConfig.debuginfo_path)
    multilib = config.Inherit(MashConfig.multilib)
    multilib_method = config.Inherit(MashConfig.multilib_method)
    arches = config.Inherit(MashConfig.arches)
    tag = config.Option()
    inherit = config.BoolOption(True)
    keys = config.Inherit(MashConfig.keys)
    strict_keys = config.Inherit(MashConfig.strict_keys)
    buildhost = config.Inherit(MashConfig.buildhost)
    repodir = config.Inherit(MashConfig.repodir)
    workdir = config.Inherit(MashConfig.workdir)
    outputdir = config.Inherit(MashConfig.outputdir)
    cachedir = config.Inherit(MashConfig.cachedir)
    compsfile = config.Inherit(MashConfig.compsfile)
    use_sqlite = config.Inherit(MashConfig.use_sqlite)
    hash = config.Inherit(MashConfig.hash)
    use_repoview = config.BoolOption(False)
    repoviewurl = config.Inherit(MashConfig.repoviewurl)
    repoviewtitle = config.Inherit(MashConfig.repoviewtitle)
    delta = config.Inherit(MashConfig.delta)
    delta_dirs = config.Inherit(MashConfig.delta_dirs)
    make_ancient = config.Inherit(MashConfig.make_ancient)
    distro_tags = config.Inherit(MashConfig.distro_tags)
    content_tags = config.Inherit(MashConfig.content_tags)
    previous = None

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
        thisdistro.keys = map(string.lower, thisdistro.keys)
        if len(thisdistro.keys) == 0:
            thisdistro.keys = ['']
        config.distros.append(thisdistro)
    
    if os.path.isdir(config.configdir):
        for file in glob.glob('%s/*.mash' % config.configdir):
            thisdistro = MashDistroConfig()
            parser = RawConfigParser()
            parser.read(file)
            for sect in parser.sections():
                thisdistro.populate(parser, sect, config)
                if not thisdistro.name:
                    thisdistro.name = sect
                if not thisdistro.repodata_path:
                    thisdistro.repodata_path = os.path.dirname(thisdistro.rpm_path)
                thisdistro.keys = map(string.lower, thisdistro.keys)
                if len(thisdistro.keys) == 0:
                    thisdistro.keys = ['']
                config.distros.append(thisdistro)
    return config

