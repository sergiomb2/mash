#!/usr/bin/python -tt

from yum import config
from ConfigParser import ConfigParser
import os
import glob

class MashConfig(config.BaseConfig):
    symlink = config.BoolOption(False)
    rpm_path = config.Option('Mash')
    debuginfo = config.BoolOption(True)
    debuginfo_path = config.Option('@ARCH@/debug')
    multilib = config.BoolOption(True)
    arches = config.ListOption()
    keys = config.ListOption()
    configdir = config.Option('/etc/mash')
    strict_keys = config.BoolOption(False)
    distros = []
    
class MashDistroConfig(config.BaseConfig):
    name = config.Option()
    symlink = config.Inherit(MashConfig.symlink)
    rpm_path = config.Inherit(MashConfig.rpm_path)
    debuginfo = config.Inherit(MashConfig.debuginfo)
    debuginfo_path = config.Inherit(MashConfig.debuginfo_path)
    multilib = config.Inherit(MashConfig.multilib)
    arches = config.Inherit(MashConfig.arches)
    tag = config.Option()
    inherit = config.BoolOption(True)
    keys = config.Inherit(MashConfig.keys)
    strict_keys = config.Inherit(MashConfig.strict_keys)

def readMainConfig(conf):
    config = MashConfig()
    parser = ConfigParser()
    parser.read(conf)
    config.populate(parser, 'defaults')
    config.parser = parser
    
    for section in config.parser.sections():
        if section == 'defaults':
            continue
        
        thisdistro = MashDistroConfig()
        thisdistro.populate(parser, section)
        config.distros.append(thisdistro)
    
    if os.path.isdir(config.configdir):
        for file in glob.glob('%s/*.mash' % config.configdir):
            thisdistro = MashDistroConfig()
            parser = ConfigParser()
            parser.read(file)
            for sect in parser.sections():
                thisdistro.populate(parser, sect, config)
                if not thisdistro.name:
                    thisdistro.name = sect
                config.distros.append(thisdistro)
    return config

