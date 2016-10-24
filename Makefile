prefix=/usr

all:

clean:
	find . -name *.pyc | xargs rm -f

install:
	install -d -m 0755 "$(DESTDIR)/$(prefix)/sbin"
	install -m 0755 syncupd "$(DESTDIR)/$(prefix)/sbin"

	install -d -m 0755 "$(DESTDIR)/$(prefix)/lib/syncupd"
	cp -r lib/* "$(DESTDIR)/$(prefix)/lib/syncupd"
	find "$(DESTDIR)/$(prefix)/lib/syncupd" -type f | xargs chmod 644
	find "$(DESTDIR)/$(prefix)/lib/syncupd" -type d | xargs chmod 755

	install -d -m 0755 "$(DESTDIR)/$(prefix)/lib/systemd/system"
	install -m 0644 data/syncupd.service "$(DESTDIR)/$(prefix)/lib/systemd/system"

	install -d -o portage -g portage -m 0755 "$(DESTDIR)/var/log/syncupd"

uninstall:
	rm -Rf "$(DESTDIR)/$(prefix)/lib/syncupd"

.PHONY: all clean install uninstall
