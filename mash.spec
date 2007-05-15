%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name:           mash
Version:        0.1.6
Release:        1%{?dist}
Summary:        Buildsystem -> tree converter
Group:          Development/Tools
License:        GPL
Source0:        %{name}-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
Requires:       yum, createrepo, koji
BuildRequires:  python-devel

BuildArch:      noarch

%description
mash is a tool that queries a koji buildsystem for the latest RPMs for
any particular tag, and creates repositories of those RPMs, including
any multlib RPMs necesary.

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


%changelog
