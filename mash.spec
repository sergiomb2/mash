%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           mash
Version:        0.1.9
Release:        1%{?dist}
Summary:        Koji buildsystem to yum repository converter
Group:          Development/Tools
License:        GPL
URL:            http://people.redhat.com/notting/mash/
Source0:        http://people.redhat.com/notting/mash/%{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Requires:       yum >= 3.1.0, createrepo, koji
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
* Wed May 23 2007 Bill Nottingham <notting@redhat.com> 0.1.9-1
- add wine, wine-arts to multilib whitelist (#241059)

* Fri May 18 2007 Bill Nottingham <notting@redhat.com> 0.1.8-1
- spec cleanups

* Thu May 17 2007 Bill Nottingham <notting@redhat.com> 0.1.7-1
- initial build
