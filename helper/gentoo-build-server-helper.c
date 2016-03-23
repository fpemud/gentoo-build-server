#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <pwd.h>

#define VALID_USER "portage"

void main(int argc, char *argv[])
{
	char *new_argv[8] = {NULL};
	struct passwd *pw = NULL;
	int i = 0;

	if (argc < 2)
	{
		fprintf(stderr, "not enough arguments\n");
		exit(1);
	}
	if (argc > 5)
	{
		fprintf(stderr, "too many arguments\n");
		exit(1);
	}

	pw = getpwuid (getuid());
	if (pw == NULL)
	{
		fprintf(stderr, "getpwuid failed: %d\n", errno);
		exit(1);
    }
	if (!strcmp(pw->pw_name, VALID_USER))
	{
		fprintf(stderr, "not run by %s\n", VALID_USER);
		exit(1);
	}

	new_argv[0] = "/usr/bin/python3";

	if (!strcmp(argv[1], "build"))
	{
		new_argv[1] = "/usr/lib/gentoo-build-server/helper_build.py";
	}
	else if (!strcmp(argv[1], "exec"))
	{
		new_argv[1] = "/usr/lib/gentoo-build-server/helper_exec.py";
	}
	else
	{
		fprintf(stderr, "invalid command\n");
		exit(1);
	}

	for (i = 1; i < argc; i++)
	{
		new_argv[i + 1] = argv[i];
	}

	execv(new_argv[0], new_argv);
	fprintf(stderr, "exec failed: %d\n", errno);
	exit(1);
}
