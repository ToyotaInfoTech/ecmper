/* SPDX-License-Identifier: GPL-2.0 */
#define _GNU_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sched.h>
#include <unistd.h>
#include <time.h>
#include <bcc/libbpf.h>

#define MAX_MAP_IDS	128

struct stat_args {

	/* arguments */
	int interval;	/* msec */
	int timeout;	/* msec */

	int show_count;
	int show_all_rx;
	int zero_clear;

	int verbose;

	int map_id[MAX_MAP_IDS];
	int map_fd[MAX_MAP_IDS];
	int nr_maps;
};

int nr_cpus;	/* number of cpus */

#define MAX_CPUS	64


/* following redirect.c */
#define COUNTER_IDX_REDIRECTED_PKTS	0
#define COUNTER_IDX_REDIRECTED_BYTES	1
#define COUNTER_IDX_RECEIVED_PKTS	2
#define COUNTER_IDX_RECEIVED_BYTES	3

double delta(unsigned long vb, unsigned long va,
	     struct timespec tb, struct timespec ta)
{
	double diff;
	double elapsed;

	diff = va - vb;

	if (ta.tv_sec == tb.tv_sec) {
		elapsed = (double)(ta.tv_nsec - tb.tv_nsec) / 1000000000.0;
	} else {
		ta.tv_sec--;
		ta.tv_nsec += 1000000000;
		elapsed = ((double)(ta.tv_sec - tb.tv_sec) +
			   (double)(ta.tv_nsec - tb.tv_nsec) / 1000000000.0);
	}

	return diff / elapsed;
}

void get_count(int map_fd, int idx, unsigned long *values)
{
	if (bpf_lookup_elem(map_fd, &idx, values) < 0) {
		perror("bpf_lookup_elem");
		exit(-1);
	}
}

struct stat {
	unsigned long pkts;
	unsigned long bytes;
	unsigned long pcpu_pkts[MAX_CPUS];
	unsigned long pcpu_bytes[MAX_CPUS];

	unsigned long all_pkts;
	unsigned long all_bytes;
	unsigned long pcpu_all_pkts[MAX_CPUS];
	unsigned long pcpu_all_bytes[MAX_CPUS];
};


void get_stat(int map_fd, struct stat *s)
{
	int n;

	memset(s, 0, sizeof(*s));

	get_count(map_fd, COUNTER_IDX_REDIRECTED_PKTS, s->pcpu_pkts);
	get_count(map_fd, COUNTER_IDX_REDIRECTED_BYTES, s->pcpu_bytes);
	get_count(map_fd, COUNTER_IDX_RECEIVED_PKTS, s->pcpu_all_pkts);
	get_count(map_fd, COUNTER_IDX_RECEIVED_BYTES, s->pcpu_all_bytes);

	for (n = 0; n < nr_cpus; n++) {
		s->pkts += s->pcpu_pkts[n];
		s->bytes += s->pcpu_bytes[n];
		s->all_pkts += s->pcpu_all_pkts[n];
		s->all_bytes += s->pcpu_all_bytes[n];
	}
}

void print_map_pcpu_stat(struct stat *stat_b, struct stat *stat_a,
			 struct timespec b, struct timespec a)
{
	int n;

	for (n = 0; n < nr_cpus; n++) {
		printf("    cpu %2d: %lf pps %lf bps\n",
		       n,
		       delta(stat_b->pcpu_pkts[n],
			     stat_a->pcpu_pkts[n],
			     b, a),
		       delta(stat_b->pcpu_bytes[n],
			     stat_a->pcpu_bytes[n],
			     b, a));
	}
}

int show_stat(struct stat_args *args)
{
	struct stat stat_a[args->nr_maps];
	struct stat stat_b[args->nr_maps];
	double pps[args->nr_maps], bps[args->nr_maps];
	double pps_sum, bps_sum;
	unsigned long pkt_cnt, byte_cnt, all_pkt_cnt, all_byte_cnt;
	struct timespec a, b;
	int n;

	while (1) {
		/* get counter values */
		clock_gettime(CLOCK_MONOTONIC, &b);
		for (n = 0; n < args->nr_maps; n++)
			get_stat(args->map_fd[n], &stat_b[n]);

		/* wait until interval ... */
		usleep(args->interval * 1000);

		/* get counter values */
		clock_gettime(CLOCK_MONOTONIC, &a);
		for (n = 0; n < args->nr_maps; n++)
			get_stat(args->map_fd[n], &stat_a[n]);

		/* calculate delta per second */
		pps_sum = 0;
		bps_sum = 0;
		pkt_cnt = 0;
		byte_cnt = 0;
		all_pkt_cnt = 0;
		all_byte_cnt = 0;
		for (n = 0; n < args->nr_maps; n++) {
			pps[n] = delta(stat_b[n].pkts, stat_a[n].pkts, b, a);
			bps[n] = delta(stat_b[n].bytes, stat_a[n].bytes, b, a);
			pps_sum += pps[n];
			bps_sum += bps[n];
			pkt_cnt += stat_a[n].pkts;
			byte_cnt += stat_a[n].bytes;
			all_pkt_cnt += stat_a[n].all_pkts;
			all_byte_cnt += stat_a[n].all_bytes;
		}

		/* print stats */
		printf("redirected throughput: %lf pps %lf bps\n",
		       pps_sum, bps_sum);
		if (args->show_count) {
			printf("redirected count: %lu pkts %lu bytes\n",
			       pkt_cnt, byte_cnt);
		}
		if (args->verbose) {
			for (n = 0; n < args->nr_maps; n++) {

				printf("  map_id %4d: %lf pps %lf bps\n",
				       args->map_id[n], pps[n], bps[n]);

				if (args->verbose > 1) {
					print_map_pcpu_stat(&stat_b[n],
							    &stat_a[n],
							    b, a);
				}
			}
		}
		if (args->show_all_rx) {
			printf("received count: %lu pkts %lu bytes\n",
			       all_pkt_cnt, all_byte_cnt);
		}

		if (args->timeout > 0) {
			if (args->timeout <= args->interval)
				break;
			args->timeout -= args->interval;
		}
	}

	return 0;
}


int num_online_cpus(void)
{
	cpu_set_t cpu_set;

	if (sched_getaffinity(0, sizeof(cpu_set), &cpu_set) == 0)
		return CPU_COUNT(&cpu_set);

	return -1;
}

int zero_clear_map(int map_fd, int idx)
{
	unsigned long value[nr_cpus];
	int ret;

	memset(value, 0, sizeof(unsigned long) * nr_cpus);
	
	ret = bpf_update_elem(map_fd, &idx, &value, BPF_ANY);
	if (ret < 0) {
		fprintf(stderr, "bpf_update_elem: %s\n", strerror(errno));
		return ret;
	}

	return 0;
}

int zero_clear_maps(struct stat_args *args)
{
	int n, ret;

	for (n = 0; n < args->nr_maps; n++) {
		int map_fd = args->map_fd[n];

		ret = zero_clear_map(map_fd, COUNTER_IDX_REDIRECTED_PKTS);
		if (ret < 0)
			return ret;

		ret = zero_clear_map(map_fd, COUNTER_IDX_REDIRECTED_BYTES);
		if (ret < 0)
			return ret;

		ret = zero_clear_map(map_fd, COUNTER_IDX_RECEIVED_PKTS);
		if (ret < 0)
			return ret;

		ret = zero_clear_map(map_fd, COUNTER_IDX_RECEIVED_BYTES);
		if (ret < 0)
			return ret;
	}

	return 0;
}

void usage(void)
{
	printf("stat: show statistics of ECMP-ER xdp\n"
	       "\n"
	       "    usage: stat [OPTIONS] [MAP ID ...]\n"
	       "\n"
	       "    MAP ID is eBPF map id. you can see it by bpftool map\n"
	       "    Multiple MAP IDs can be specified.\n"
	       "\n"
	       "    -i INTERVAL    interval (sec)\n"
	       "    -t TIMEOUT     timeout (sec)\n"
	       "    -c             show counters\n"
	       "    -a             show counters of all received packets\n"
	       "    -z             set counters in maps to 0 when starting\n"
	       "    -v             enable verbose output\n"
	       "    -h             print this help\n"
	       "\n");
}

int main(int argc, char **argv)
{
	struct stat_args args;
	int ch, n;
	double i;

	memset(&args, 0, sizeof(args));
	args.interval = 1000; /* 1 sec */

	while ((ch = getopt(argc, argv, "i:t:cazvh")) != -1) {
		switch (ch) {

		case 'i':
			if (sscanf(optarg, "%lf", &i) != 1) {
				fprintf(stderr, "invalid interval %s\n",
					optarg);
				return -1;
			}
			args.interval = i * 1000;
			break;

		case 't':
			if (sscanf(optarg, "%lf", &i) != 1) {
				fprintf(stderr, "invalid timeout %s\n",
					optarg);
				return -1;
			}
			args.timeout = i * 1000;
			break;

		case 'c':
			args.show_count = 1;
			break;

		case 'a':
			args.show_all_rx = 1;
			break;

		case 'z':
			args.zero_clear = 1;
			break;

		case 'v':
			args.verbose++;
			break;

		case 'h':
		default:
			usage();
			return -1;
		}
	}

	for (n = optind; n < argc; n++) {
		int map_id = atoi(argv[n]);

		if (map_id < 1) {
			printf("invalid map id %s\n", argv[n]);
			return -1;
		}
		args.map_id[args.nr_maps++] = map_id;
	}


	nr_cpus = num_online_cpus();
	if (nr_cpus < 0) {
		fprintf(stderr, "failed to get number of cpus: %s\n",
			strerror(errno));
		return -1;
	}
	if (nr_cpus > MAX_CPUS) {
		fprintf(stderr, "sorry, too many cpus\n");
		return -1;
	}


	if (args.verbose) {
		printf("interval:   %d (msec)\n", args.interval);
		printf("timeout:    %d (msec)\n", args.timeout);
		printf("show count: %s\n", args.show_count ? "on" : "off");
		printf("zero clear: %s\n", args.zero_clear ? "on" : "off");
		printf("verbose:    %d\n", args.verbose);
		printf("nr_maps:    %d\n", args.nr_maps);
		for (n = 0; n < args.nr_maps; n++) {
			printf("    map id: %d\n", args.map_id[n]);
		}
	}


	for (n = 0; n < args.nr_maps; n++) {
		args.map_fd[n] = bpf_map_get_fd_by_id(args.map_id[n]);
		if (args.map_fd[n] < 0) {
			fprintf(stderr,
				"failed to get fd for the map id %d: %s\n",
				args.map_id[n], strerror(errno));
			return -1;
		}
	}

	if (args.zero_clear)
		if (zero_clear_maps(&args) < 0)
			return -1;

	return show_stat(&args);
}
