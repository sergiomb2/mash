
import os
import glob
import string

from ConfigParser import RawConfigParser

from yum import config

class MashConfig(config.BaseConfig):
    symlink = config.BoolOption(False)
    fork = config.BoolOption(True)
    rpm_path = config.Option('Mash')
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
    buildhost = config.Option()
    repodir = config.Option('/mnt/koji')
    compsfile = config.Option()
    use_sqlite = config.BoolOption(True)
    show_broken_deps = config.BoolOption(False)
    distros = []
    
class MashDistroConfig(config.BaseConfig):
    name = config.Option()
    symlink = config.Inherit(MashConfig.symlink)
    fork = config.Inherit(MashConfig.fork)
    rpm_path = config.Inherit(MashConfig.rpm_path)
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
    compsfile = config.Inherit(MashConfig.compsfile)
    use_sqlite = config.Inherit(MashConfig.use_sqlite)
    show_broken_deps = config.Inherit(MashConfig.show_broken_deps)

def readMainConfig(conf):
    config = MashConfig()
    parser = RawConfigParser()
    parser.read(conf)
    config.populate(parser, 'defaults')
    config.parser = parser
    config.keys = map(string.lower, config.keys)
    
    for section in config.parser.sections():
        if section == 'defaults':
            continue
        
        thisdistro = MashDistroConfig()
        thisdistro.populate(parser, section)
        thisdistro.keys = map(string.lower, thisdistro.keys)
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
                thisdistro.keys = map(string.lower, thisdistro.keys)
                config.distros.append(thisdistro)
    return config

