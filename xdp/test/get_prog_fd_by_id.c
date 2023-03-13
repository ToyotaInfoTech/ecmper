#include <stdio.h>
#include <stdlib.h>
#include <bcc/libbpf.h>


int main(int argc, char **argv)
{
	int id = 0;
	int fd;

	id = atoi(argv[1]);
	printf("id is %d\n", id);

	fd = bpf_prog_get_fd_by_id(id);
	printf("bpf_prog_get_fd_by_id returns %d\n", fd);

	return 0;
}
