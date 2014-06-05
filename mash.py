#!/usr/bin/python

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

import sys
import os

from optparse import OptionParser

import mash
import mash.config
    
def main():
    usage = "usage: %prog [options] <configuration to build>"
    parser = OptionParser(usage, version='%prog 0.6.9')
    parser.add_option("-o","--outputdir",default="", dest="outputdir",
      help="output directory")
    parser.add_option("-c","--config", default="/etc/mash/mash.conf", dest="config",
      help="configuration file to use")
    parser.add_option("-f","--compsfile", default="", dest="compsfile",
      help="comps file to use")
    parser.add_option("-p","--previous", default="", dest="previous",
      help="previous mash run to use as basis for createrepo")
    parser.add_option("-d","--delta", action='append', dest="delta",
      help="previous directory to use for deltarpm creation")
    parser.add_option("--no-delta", action='store_false', dest="do_delta",
      default=True, help="do not compose the deltarpms")
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
        if opts.outputdir[0] != '/':
            opts.outputdir = os.path.realpath(os.path.join(os.getcwd(), opts.outputdir))
        for dist in conf.distros:
            dist.outputdir = opts.outputdir
    if opts.compsfile != "":
        for dist in conf.distros:
            dist.compsfile = opts.compsfile
    if opts.delta and opts.delta != []:
        for dist in conf.distros:
            dist.delta_dirs = opts.delta
    if opts.previous != "":
        if opts.previous[0] != '/':
            opts.previous = os.path.realpath(os.path.join(os.getcwd(), opts.previous))
        for dist in conf.distros:
            dist.previous = opts.previous
            if not dist.delta_dirs:
                dist.delta_dirs = [os.path.join(opts.previous, dist.rpm_path)]
    if not opts.do_delta:
        for dist in conf.distros:
            dist.delta = False

    dists = []
    for dist in conf.distros:
        if dist.name == args[0]:
            themash = mash.Mash(dist)
        
            # HAAACK
            pid = os.fork()
            if pid == 0:
                rc = themash.doCompose()
                os._exit(rc)
            else:
                (p, status) = os.waitpid(pid,0)
            if not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
                print "mash failed in %s" % os.path.join(dist.outputdir, 
                                                         dist.output_subdir)
                sys.exit(1)
            if themash.config.multilib:
                rc = themash.doMultilib()
                if rc:
                    print "mash failed in %s" % os.path.join(dist.outputdir, 
                                                             dist.output_subdir)
                    sys.exit(1)
            print "mash done in %s" % os.path.join(dist.outputdir, 
                                                   dist.output_subdir)
            sys.exit(0)

    print "ERROR: No configuration named '%s'!\n" % (args[0],)
    parser.print_help()
    sys.exit(1)

if __name__ == '__main__':
    main()
