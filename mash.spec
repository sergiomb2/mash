%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           mash
Version:        0.3.1
Release:        1%{?dist}
Summary:        Koji buildsystem to yum repository converter
Group:          Development/Tools
License:        GPL
URL:            http://people.redhat.com/notting/mash/
Source0:        http://people.redhat.com/notting/mash/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Requires:       yum, createrepo >= 0.9.2, koji
Conflicts:	pungi < 1.0.0
BuildRequires:  python-devel
BuildArch:      noarch

%description
mash is a tool that queries a koji buildsystem for the latest RPMs for
any particular tag, and creates repositories of those RPMs, including
any multlib RPMs that are necessary.

%prep
%setup -q

%build
%{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT

mv $RPM_BUILD_ROOT/%{_bindir}/mash.py $RPM_BUILD_ROOT/%{_bindir}/mash
 
%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc AUTHORS ChangeLog COPYING README TODO
%config(noreplace) %{_sysconfdir}/mash
%{python_sitelib}/mash*
%{_bindir}/*
%{_datadir}/mash

%changelog
* Fri Feb 22 2008 Bill Nottingham <notting@redhat.com> 0.3.1-1
- fix yum api usage (#433555, <peter@pramberger.at>)
- fix noarch w/o src.rpm logic (#433551, <peter@pramberger.at>)
- Add a 'use_repoview' option that allows us to toggle repoview generation. (<lmacken@redhat.com>)
- Tell createrepo to be quiet (<lmacken@redhat.com>)
- Don't re-generate repoview after multilib solving. (<lmacken@redhat.com>)
- Fix our "failsafe" shutil.copyfile call (<lmacken@redhat.com>)

* Thu Jan 17 2008 Bill Nottingham <notting@redhat.com> 0.3.0-1
- use createrepo's python API
- allow running without local koji storage

* Mon Nov 19 2007 Bill Nottingham <notting@redhat.com> 0.2.10-1
- handle non Packages/ repositories better (#350391)

* Fri Nov  9 2007 Bill Nottingham <notting@redhat.com> 0.2.9-1
- handle noarch excludearch for packages without source
  rpms (<rob.myers@gtri.gatech.edu>)
- use yum's pkgSack, not yumLocalPackage

* Tue Sep 25 2007 Bill Nottingham <notting@redhat.com> 0.2.8-1
- libflashsupport (#305541)

* Fri Sep 21 2007 Bill Nottingham <notting@redhat.com> 0.2.7-1
- disable repoview for now

* Thu Sep 20 2007 Bill Nottingham <notting@redhat.com> 0.2.6-1
- repoview cleanups/fixes
- fix gtkimmodules typo (#295371, <petersen@redhat.com>)

* Tue Sep 18 2007 Bill Nottingham <notting@redhat.com> 0.2.5-1
- handle valgrind for multilib differently (#294761)

* Mon Sep 17 2007 Bill Nottingham <notting@redhat.com> 0.2.4-1
- repoview support (<jkeating@redhat.com>)

* Thu Sep  6 2007 Bill Nottingham <notting@redhat.com> 0.2.3-1
- blacklist java-1.7.0-icedtea-devel (#271761)

* Tue Sep  4 2007 Bill Nottingham <notting@redhat.com> 0.2.2-1
- add nspluginwrapper to multilib whitelist (#275021)
- fix kernel-devel (#247321)

* Tue Aug 28 2007 Bill Nottingham <notting@redhat.com> 0.2.0-1
- updates to work with pungi 1.0.0, conflict with older pungi
- fix some multilib compose issues (<drago01@gmail.com>)

* Mon Jul 23 2007 Bill Nottingham <notting@redhat.com> 0.1.19-1
- fix spam-o-matic to use python mailer

* Thu Jun 21 2007 Bill Nottingham <notting@redhat.com> 0.1.18-1
- pull in cyrus-sasl plugins (#245176)

* Thu Jun  7 2007 Bill Nottingham <notting@redhat.com> 0.1.17-1
- exclude debuginfo from repodata where appropriate
- add spam-o-matic

* Thu May 31 2007 Bill Nottingham <notting@redhat.com> 0.1.16-1
- fix arch handling

* Thu May 31 2007 Bill Nottingham <notting@redhat.com> 0.1.15-1
- propagate errors better
- handle signatures in koji correctly

* Wed May 30 2007 Bill Nottingham <notting@redhat.com> 0.1.14-1
- add a use_sqlite config option for determining whether to use createrepo -d

* Wed May 30 2007 Bill Nottingham <notting@redhat.com> 0.1.13-1
- hopefully fix the db locking issues
- make source rpm path configurable
- add updates config files

* Tue May 29 2007 Bill Nottingham <notting@redhat.com> 0.1.12-1
- use /tmp where appropriate
- hacks to use less memory

* Sat May 26 2007 Bill Nottingham <notting@redhat.com> 0.1.11-1
- run more operations in parallel

* Thu May 24 2007 Bill Nottingham <notting@redhat.com> 0.1.10-1
- fix kernel handling
- tweak rawhide config

* Wed May 23 2007 Bill Nottingham <notting@redhat.com> 0.1.9-1
- add wine, wine-arts to multilib whitelist (#241059)

* Fri May 18 2007 Bill Nottingham <notting@redhat.com> 0.1.8-1
- spec cleanups

* Thu May 17 2007 Bill Nottingham <notting@redhat.com> 0.1.7-1
- initial build
