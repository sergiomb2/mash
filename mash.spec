%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           mash
Version:        0.1.19
Release:        1%{?dist}
Summary:        Koji buildsystem to yum repository converter
Group:          Development/Tools
License:        GPL
URL:            http://people.redhat.com/notting/mash/
Source0:        http://people.redhat.com/notting/mash/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Requires:       yum, createrepo, koji
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
%{python_sitelib}/mash
%{_bindir}/*
%{_datadir}/mash

%changelog
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
