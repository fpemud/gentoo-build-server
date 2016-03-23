prefix=/usr

all:

clean:
	find . -name *.pyc | xargs rm -f

install:
	install -d -m 0755 "$(DESTDIR)/$(prefix)/sbin"
	install -m 0755 gentoo-build-server "$(DESTDIR)/$(prefix)/sbin"

	install -d -m 0755 "$(DESTDIR)/$(prefix)/lib/gentoo-build-server"
	cp -r lib/* "$(DESTDIR)/$(prefix)/lib/gentoo-build-server"
	find "$(DESTDIR)/$(prefix)/lib/gentoo-build-server" -type f | xargs chmod 644
	find "$(DESTDIR)/$(prefix)/lib/gentoo-build-server" -type d | xargs chmod 755

	$(CC) $(LDFLAGS) libexec/gentoo-build-server-helper.c $(LIBS) -o libexec/gentoo-build-server-helper
	install -d -m 0755 "$(DESTDIR)/$(prefix)/libexec"
	install -m 0755 libexec/gentoo-build-server-helper "$(DESTDIR)/$(prefix)/libexec"
	rm libexec/gentoo-build-server-helper

	install -d -m 0755 "$(DESTDIR)/$(prefix)/lib/systemd/system"
	install -m 0644 data/gentoo-build-server.service "$(DESTDIR)/$(prefix)/lib/systemd/system"

	install -d -o portage -g portage -m 0755 "$(DESTDIR)/var/log/gentoo-build-server"

uninstall:
	rm -Rf "$(DESTDIR)/$(prefix)/lib/gentoo-build-server"

.PHONY: all clean install uninstall
