#!/usr/bin/python

import sys
import os

from optparse import OptionParser

import mash
import mash.config
    
def main():
    usage = "usage: %prog [options] <configuration to build>"
    parser = OptionParser(usage, version='%prog 0.1.14')
    parser.add_option("-o","--outputdir",default="", dest="outputdir",
      help="output directory")
    parser.add_option("-c","--config", default="/etc/mash/mash.conf", dest="config",
      help="configuration file to use")
    parser.add_option("-f","--compsfile", default="", dest="compsfile",
      help="comps file to use")
    (opts, args) = parser.parse_args()
    
    if len(args) < 1:
        print "ERROR: No configuration specified!\n"
        parser.print_help()
        sys.exit(1)
    if len(args) > 1:
        print "ERROR: Only one configuration at a time, please.\n"
        parser.print_help()
        sys.exit(1)
    
    conf = mash.config.readMainConfig(opts.config)
    
    if opts.outputdir != "":
        conf.workdir = opts.outputdir
        for dist in conf.distros:
            dist.workdir = opts.outputdir
    if opts.compsfile != "":
        conf.compsfile = opts.compsfile
        for dist in conf.distros:
            dist.compsfile = opts.compsfile
        
    dists = []
    for dist in conf.distros:
        if dist.name == args[0]:
            themash = mash.Mash(dist)
        
            # HAAACK
            pid = os.fork()
            if pid == 0:
                rc = themash.doCompose()
                print rc
                os._exit(rc)
            else:
                (p, status) = os.waitpid(pid,0)
            if not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
                print "mash failed in %s" % os.path.join(conf.workdir, dist.name)
                sys.exit(1)
            rc = themash.doMultilib()
            if rc:
                print "mash failed in %s" % os.path.join(conf.workdir, dist.name)
                sys.exit(1)
            print "mash done in %s" % os.path.join(conf.workdir, dist.name)
            sys.exit(0)

    print "ERROR: No configuration named '%s'!\n" % (args[0],)
    parser.print_help()
    sys.exit(1)

if __name__ == '__main__':
    main()
