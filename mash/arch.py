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

# Unfortunately, rpmUtils.arch is not what we want.


compat = { "i386" : ("athlon", "i686", "i586", "i486", "i386", "noarch"),
           "x86_64" : ("amd64", "ia32e", "x86_64", "noarch"),
           "ia64" : ("ia64", "noarch"),
           "ppc" : ("ppc", "noarch"),
           "ppc64" : ("ppc64pseries", "ppc64iseries", "ppc64", "noarch"),
           "s390" : ("s390", "noarch"),
           "s390x" : ("s390x",  "noarch"),
           "sparc" : ("sparcv9v", "sparcv9", "sparcv8", "sparc", "noarch"),
           "sparc64" : ("sparc64v", "sparc64", "noarch"),
           "alpha" : ("alphaev6", "alphaev56", "alphaev5", "alpha", "noarch"),
           "arm" : ("arm", "armv4l", "armv4tl", "armv5tel", "armv5tejl", "armv6l", "armv7l", "noarch"),
           "armhfp" : ("armv7hl", "armv7hnl", "noarch"),
}

biarch = { "ppc" : "ppc64", "x86_64" : "i386", "sparc" : "sparc64", "s390x" : "s390" }

           
