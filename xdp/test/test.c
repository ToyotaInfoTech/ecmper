#define _GNU_SOURCE

#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <sched.h>
#include <unistd.h>
#include <bcc/libbpf.h>

int num_online_cpus(void)
{
	cpu_set_t cpu_set;

	if (sched_getaffinity(0, sizeof(cpu_set), &cpu_set) == 0)
		return CPU_COUNT(&cpu_set);

	return -1;
}

int main(int argc, char **argv)
{
	int map_fd;

	map_fd = bpf_obj_get("/sys/fs/bpf/xdp/globals/redirect_counter");
	printf("map_fd is %d\n", map_fd);
	if (map_fd < 0) {
		perror("bpf_obj_get");
		return -1;
	}

	int ret;
	int key = 1;
	int nr_cpus = num_online_cpus();

	if (nr_cpus < 0) {
		printf("failed to get online cpus\n");
		return -1;
	}
		
	unsigned long value[nr_cpus];
	memset(value, 0, sizeof(value));

	ret = bpf_update_elem(map_fd, &key, &value, BPF_NOEXIST);
	if (ret < 0) {
		printf("update_elem retruns %d\n", ret);
		perror("bpf_update_elem");
	}

	while (1) {
		int n;

		ret = bpf_lookup_elem(map_fd, &key, &value);
		if (ret < 0) {
			perror("bpf_lookup_elem");
			return -1;
		}
		for (n = 0; n < nr_cpus; n++) {
			printf("value[%d] is %lu\n", n, value[n]);
		}
		sleep(1);
	}

	return 0;
}
