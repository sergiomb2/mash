
import os
import shutil

import rpm

usenew = True
try:
    import createrepo
except:
    usenew = False

class MetadataOld:
    def __init__(self, logger):
        self.args = [ 'createrepo', '--update', '-q' ]
        self.previous = None
        self.logger = logger

    def set_cachedir(self, path):
        self.args.append('-c')
        self.args.append(path)

    def set_comps(self, comps):
        self.args.append('-g')
        self.args.append(comps)

    def set_excludes(self, excludes):
        self.args.append('-x')
        self.args.append(excludes)

    def set_database(self, db):
        self.args.append('-d')

    def set_skipstat(self, skip):
        self.args.append('--skip-stat')

    def set_previous(self, previous):
        self.previous = previous

    def run(self, path):
        self.args.append(path)
        if self.previous:
            try:
                shutil.copytree(self.previous, "%s/repodata" % (path,))
            except OSError:
                self.logger.error("Couldn't copy repodata from %s" % (self.previous,))
        pid = os.fork()
        if not pid:
            os.execv("/usr/bin/createrepo", self.args)
        else:
            (p, status) = os.waitpid(pid, 0)

class MetadataNew:
    def __init__(self, logger):
        self.conf = createrepo.MetaDataConfig()
        self.conf.update = True
        self.conf.quiet = True
        self.conf.unique_md_filenames = True
        self.previous = None
        self.logger = logger

    def set_cachedir(self, path):
        self.conf.cachedir = path

    def set_comps(self, comps):
        self.conf.groupfile = comps

    def set_excludes(self, excludes):
        self.conf.excludes.append(excludes)

    def set_database(self, db):
        self.conf.database = db

    def set_skipstat(self, skip):
        self.conf.skip_stat = skip

    def set_previous(self, previous):
        if rpm.labelCompare([createrepo.__version__,'0','0'], ['0.9.7', '0', '0']) >= 0:
              self.conf.update_md_path = previous
        else:
              self.previous = previous

    def run(self, path):
        self.conf.outputdir = path
        self.conf.directory = path
        if self.previous:
            try:
                shutil.copytree(self.previous, "%s/repodata" % (path,))
            except OSError:
                self.logger.error("Couldn't copy repodata from %s" % (self.previous,))
        repomatic = createrepo.MetaDataGenerator(self.conf)
        repomatic.doPkgMetadata()
        repomatic.doRepoMetadata()
        repomatic.doFinalMove()

class Metadata:
    def __init__(self, logger):
        if usenew:
            self.obj = MetadataNew(logger)
        else:
            self.obj = MetadataOld(logger)

    def set_cachedir(self, path):
        self.obj.set_cachedir(path)

    def set_comps(self, comps):
        self.obj.set_comps(comps)

    def set_excludes(self, excludes):
        self.obj.set_excludes(excludes)

    def set_database(self, db):
        self.obj.set_database(db)

    def set_skipstat(self, skip):
        self.obj.set_skipstat(skip)

    def set_previous(self, previous):
        self.obj.set_previous(previous)

    def run(self, path):
        self.obj.run(path)
