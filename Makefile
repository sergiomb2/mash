PKGNAME=mash
VERSION=$(shell rpm -q --qf "%{VERSION}\n" --specfile ${PKGNAME}.spec)
RELEASE=$(shell rpm -q --qf "%{RELEASE}\n" --specfile ${PKGNAME}.spec)
TAG=$(VERSION)
PKGRPMFLAGS=--define "_topdir ${PWD}" --define "_specdir ${PWD}" --define "_sourcedir ${PWD}/dist" --define "_srcrpmdir ${PWD}" --define "_rpmdir ${PWD}" --define "_builddir ${PWD}"

RPM="noarch/${PKGNAME}-$(VERSION)-$(RELEASE).noarch.rpm"
SRPM="${PKGNAME}-$(VERSION)-$(RELEASE).src.rpm"


default: all

all:
	@echo "Nothing to do"

tag:
	@git tag -a -m "Tag as $(TAG)" $(TAG)
	@echo "Tagged as $(TAG)"

archive: tag clean
	@rm -rf ${PKGNAME}-$(VERSION)/
	@python setup.py sdist > /dev/null
	@echo "The archive is in dist/${PKGNAME}-$(VERSION).tar.gz"

srpm: archive
	@rm -f $(SRPM)
	@rpmbuild -bs ${PKGRPMFLAGS} ${PKGNAME}.spec
	@echo "The srpm is in $(SRPM)"

rpm: archive
	@rpmbuild --clean -bb ${PKGRPMFLAGS} ${PKGNAME}.spec
	@echo "The rpm is in $(RPM)"

rpminstall: rpm
	@rpm -ivh --force $(RPM)

release: tag srpm

clean:
	@rm -f *.rpm 
	@rm -rf noarch
	@rm -f *.tar.gz
	@rm -rf dist
	@rm -f MANIFEST
	@find . -name "*~" -exec rm -f {} \;
	@find . -name "*.pyc" -exec rm -f {} \;
