
# Unfortunately, rpmUtils.arch is not what we want.


compat = { "i386" : ("athlon", "i686", "i586", "i486", "i386", "noarch"),
           "x86_64" : ("x86_64", "ia32e", "amd64", "noarch"),
           "ia64" : ("ia64", "noarch"),
           "ppc" : ("ppc", "noarch"),
           "ppc64" : ("ppc64", "ppc64iseries", "ppc64pseries", "noarch"),
           "s390" : ("s390", "noarch"),
           "s390x" : ("s390x",  "noarch"),
           "sparc" : ("sparcv9v", "sparcv9", "sparcv8", "sparc", "noarch"),
           "sparc64" : ("sparc64v", "sparc64", "noarch"),
           "alpha" : ("alphaev6", "alphaev56", "alphaev5", "alpha", "noarch"),
}

biarch = { "ppc" : "ppc64", "x86_64" : "i386", "sparc" : "sparc64", "s390x" : "s390" }

           
           