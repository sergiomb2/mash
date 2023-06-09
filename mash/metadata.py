
import locale
import os
import os.path
import shutil
import time

import rpm
import rpmUtils
import rpmUtils.miscutils

usenew = True
try:
    import createrepo
except:
    usenew = False


def _make_ancient(path, excludes, previous, logger):
    args = ["yum-arch", "-q", "-s"]
    for exclude in excludes:
        args = args + ["-x", exclude]
    args.append(path)
    if previous:
        try:
            shutil.copytree("%s/headers" % (previous,), "%s/headers" % (path,))
        except OSError:
            logger.error("Couldn't copy repodata from %s" % (previous,))
    pid = os.fork()
    if not pid:
        os.execv("/usr/bin/yum-arch", args)
    else:
        (p, status) = os.waitpid(pid, 0)
    return status


class MetadataOld:

    def __init__(self, logger):
        self.args = ['createrepo', '--update', '-q']
        self.previous = None
        self.logger = logger
        self.excludes = []
        self.ancient = False

    def set_ancient(self, ancient):
        self.ancient = ancient

    def set_cachedir(self, path):
        self.args.append('-c')
        self.args.append(path)

    def set_comps(self, comps):
        self.args.append('-g')
        self.args.append(comps)

    def set_excludes(self, excludes):
        self.args.append('-x')
        self.args.append(excludes)
        self.excludes.append(excludes)

    def set_database(self, db):
        self.args.append('-d')

    def set_compress_type(self, compress_type):
        self.args.append('--compress-type')
        self.args.append(compress_type)

    def set_hash(self, hashtype):
        # Sorry, can't do that here.
        pass

    def set_skipstat(self, skip):
        if skip:
            self.args.append('--skip-stat')

    def set_delta(self, deltapaths, max_delta_rpm_size, max_delta_rpm_age, delta_workers):
        # Sorry, can't do that here.
        pass

    def set_previous(self, previous):
        self.previous = previous

    def set_distro_tags(self, distro_tags):
        # Sorry, can't do that here.
        pass

    def set_content_tags(self, content_tags):
        # Sorry, can't do that here.
        pass

    def run(self, path):
        self.args.append(path)
        if self.previous:
            try:
                shutil.copytree("%s/repodata" %
                                (self.previous,), "%s/repodata" % (path,))
            except OSError:
                self.logger.error(
                    "Couldn't copy repodata from %s" % (self.previous,))
        pid = os.fork()
        if not pid:
            os.execv("/usr/bin/createrepo", self.args)
        else:
            (p, status) = os.waitpid(pid, 0)
        if self.ancient:
            _make_ancient(path, self.excludes, self.previous, self.logger)


class MetadataNew:

    def __init__(self, logger):
        self.conf = createrepo.MetaDataConfig()
        self.conf.update = True
        self.conf.quiet = True
        self.conf.unique_md_filenames = True
        self.conf.excludes = []
        self.previous = None
        self.logger = logger
        self.ancient = False

    def set_ancient(self, ancient):
        self.ancient = ancient

    def set_cachedir(self, path):
        self.conf.cachedir = path

    def set_comps(self, comps):
        self.conf.groupfile = comps

    def set_excludes(self, excludes):
        self.conf.excludes.append(excludes)

    def set_database(self, db):
        self.conf.database = db

    def set_compress_type(self, compress_type):
        self.conf.compress_type = compress_type

    def set_hash(self, hashtype):
        self.conf.sumtype = hashtype

    def set_skipstat(self, skip):
        self.conf.skip_stat = skip

    def set_delta(self, deltapaths, max_delta_rpm_size, max_delta_rpm_age, delta_workers):
        if rpm.labelCompare([createrepo.__version__, '0', '0'], ['0.9.7', '0', '0']) >= 0:
            self.conf.deltas = True
            self.conf.oldpackage_paths = deltapaths
            self.conf.max_delta_rpm_size = max_delta_rpm_size
            self.conf.max_delta_rpm_age = max_delta_rpm_age
            self.conf.delta_workers = delta_workers

    def set_previous(self, previous):
        if rpm.labelCompare([createrepo.__version__, '0', '0'], ['0.9.7', '0', '0']) >= 0:
            self.conf.update_md_path = previous
        self.previous = previous

    def set_distro_tags(self, distro_tags):
        self.conf.distro_tags = [distro_tags]

    def set_content_tags(self, content_tags):
        self.conf.content_tags = content_tags

    def _copy_in_deltas(self, path):
        if not os.path.exists('%s/drpms' % (path,)):
            os.mkdir('%s/drpms' % (path,))

        ts = rpmUtils.transaction.initReadOnlyTransaction()
        ts.pushVSFlags((rpm._RPMVSF_NOSIGNATURES | rpm._RPMVSF_NODIGESTS))

        def _sigmatches(hdr, filename):
            newhdr = rpmUtils.miscutils.hdrFromPackage(ts, filename)
            locale.setlocale(locale.LC_ALL, 'C')
            string = '%|DSAHEADER?{%{DSAHEADER:pgpsig}}:{%|RSAHEADER?{%{RSAHEADER:pgpsig}}:{%|SIGGPG?{%{SIGGPG:pgpsig}}:{%|SIGPGP?{%{SIGPGP:pgpsig}}:{(none)}|}|}|}|'
            siginfo1 = hdr.sprintf(string)
            siginfo2 = newhdr.sprintf(string)
            if siginfo1 == siginfo2:
                return True

        def _matches(file, list):
            hdr = rpmUtils.miscutils.hdrFromPackage(ts, file)
            fname = '%s-%s-%s.%s.rpm' % (
                hdr['name'], hdr['version'], hdr['release'], hdr['arch'])
            if fname in list.keys():
                # if _sigmatches(hdr, list[fname]):
                return True
            return False

        def _copy(file, path):
            destpath = '%s/drpms/%s' % (path, os.path.basename(file))

            modified_time = os.path.getmtime(file)
            age = time.time() - modified_time

            # If max_delta_rpm_age is None, then don't worry about it.
            if self.conf.max_delta_rpm_age and age > self.conf.max_delta_rpm_age:
                return

            try:
                os.link(file, destpath)
            except OSError:
                shutil.copy2(file, destpath)

        fulllist = self.repomatic.getFileList(self.conf.directory, '.rpm')
        filelist = {}
        for f in fulllist:
            filelist[os.path.basename(f)] = os.path.join(
                self.conf.directory, f)
        deltalist = self.repomatic.getFileList(
            '%s/drpms' % (self.previous,), '.drpm')
        for file in deltalist:
            fullpath = '%s/drpms/%s' % (self.previous, file)
            if _matches(fullpath, filelist):
                _copy(fullpath, path)

    def run(self, path):
        self.conf.outputdir = path
        self.conf.directory = path
        self.repomatic = createrepo.MetaDataGenerator(self.conf)
        if self.previous:
            if not self.conf.update_md_path:
                try:
                    shutil.copytree("%s/repodata" %
                                    (self.previous,), "%s/repodata" % (path,))
                except OSError:
                    self.logger.error(
                        "Couldn't copy repodata from %s" % (self.previous,))
            if self.conf.deltas:
                self._copy_in_deltas(path)
        self.repomatic.doPkgMetadata()
        self.repomatic.doRepoMetadata()
        self.repomatic.doFinalMove()
        if self.ancient:
            _make_ancient(path, self.conf.excludes, self.previous, self.logger)


class Metadata:

    def __init__(self, logger):
        if usenew:
            self.obj = MetadataNew(logger)
        else:
            self.obj = MetadataOld(logger)

    def set_ancient(self, ancient):
        self.obj.set_ancient(ancient)

    def set_cachedir(self, path):
        self.obj.set_cachedir(path)

    def set_comps(self, comps):
        self.obj.set_comps(comps)

    def set_excludes(self, excludes):
        self.obj.set_excludes(excludes)

    def set_database(self, db):
        self.obj.set_database(db)

    def set_hash(self, hashtype):
        self.obj.set_hash(hashtype)

    def set_compress_type(self, compress_type):
        self.obj.set_compress_type(compress_type)

    def set_skipstat(self, skip):
        self.obj.set_skipstat(skip)

    def set_delta(self, deltapaths, max_delta_rpm_size, max_delta_rpm_age, delta_workers):
        self.obj.set_delta(
            deltapaths, max_delta_rpm_size, max_delta_rpm_age, delta_workers)

    def set_previous(self, previous):
        self.obj.set_previous(previous)

    def set_distro_tags(self, distro_tags):
        split_tag = distro_tags.split(' ', 1)
        self.obj.set_distro_tags(split_tag)

    def set_content_tags(self, content_tags):
        self.obj.set_content_tags(content_tags)

    def run(self, path):
        self.obj.run(path)
