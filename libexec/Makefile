all: gentoo-build-server-helper

gentoo-build-server-helper: gentoo-build-server-helper.o
	$(CC) $(LDFLAGS) $^ $(LIBS) -o $@

clean:
	rm -f gentoo-build-server-helper *.o
