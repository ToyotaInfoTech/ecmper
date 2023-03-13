/* SPDX-License-Identifier: GPL-2.0 */
#define KBUILD_MODNAME "foo"

#include <linux/if_ether.h>
#include <linux/in.h>
#include <linux/ip.h>
#include <linux/tcp.h>

#include "bpf.h"
#include "bpf_helpers.h"
#include "bpf_endian.h"

#ifndef memcpy
#define memcpy(dest, src, n)	__builtin_memcpy((dest), (src), (n))
#endif

//#define REDIRECT_DEBUG

#define ECMP_ER_TOS_RETRANSMITTED 	0x01

#ifdef REDIRECT_DEBUG
#define trace_printk(fmt, ...)						\
	do {								\
		char __fmt[] = fmt;					\
		bpf_trace_printk(__fmt, sizeof(__fmt), ##__VA_ARGS__);	\
	} while (0)
#else
#define trace_printk(fmt, ...) {}
#endif

/* packet counter */
#define COUNTER_IDX_REDIRECTED_PKTS	0
#define COUNTER_IDX_REDIRECTED_BYTES	1
#define COUNTER_IDX_RECEIVED_PKTS	2
#define COUNTER_IDX_RECEIVED_BYTES	3

#define PIN_GLOBAL_NS           2
struct bpf_elf_map {
	__u32 type;
	__u32 key_size;
	__u32 value_size;
	__u32 max_entries;
	__u32 flags;
	__u32 id;
	__u32 pinning;
};

#if 0
struct bpf_map_def SEC("maps") redirect_counter = {
	.type = BPF_MAP_TYPE_PERCPU_ARRAY,
	.key_size = sizeof(int),
	.value_size = sizeof(long),
	.max_entries = 16,
};
#endif

struct bpf_elf_map SEC("maps") redirect_counter = {
	.type = BPF_MAP_TYPE_PERCPU_ARRAY,
	.key_size = sizeof(int),
	.value_size = sizeof(long),
	.max_entries = 16,
	.pinning = 0,	/* no pin */
};


static __u16 update_checksum(__u16 cksum, __u16 old, __u16 new)
{
        __u32 new_cksum;

        new_cksum = (__u16)~cksum + (__u16)~old + new;
        new_cksum = (new_cksum >> 16) + (new_cksum & 0xFFFF);
        return (__u16)(~new_cksum);
}

static void update_received_counter(struct xdp_md *ctx)
{
	int key;
	unsigned long *value;

	key = COUNTER_IDX_RECEIVED_PKTS;
	value = bpf_map_lookup_elem(&redirect_counter, &key);
	if (value)
		*value += 1;

	key = COUNTER_IDX_RECEIVED_BYTES;
	value = bpf_map_lookup_elem(&redirect_counter, &key);
	if (value)
		*value += (ctx->data_end - ctx->data);
}

static void update_redirected_counter(struct xdp_md *ctx)
{
	trace_printk("exec: update_redirected_counter");
	int key;
	unsigned long *value;

	key = COUNTER_IDX_REDIRECTED_PKTS;
	value = bpf_map_lookup_elem(&redirect_counter, &key);
	if (value)
		*value += 1;

	key = COUNTER_IDX_REDIRECTED_BYTES;
	value = bpf_map_lookup_elem(&redirect_counter, &key);
	if (value)
		*value += (ctx->data_end - ctx->data);
}

static void xfrm_for_retransmit(struct ethhdr *eth, struct iphdr *iph)
{
	trace_printk("exec: xfrm_for_retransmit");
	/* update ToS and checksum */
	__u16 before, after;
	before = *((__u16 *)iph);
	iph->tos = ECMP_ER_TOS_RETRANSMITTED;
	after = *((__u16 *)iph);
	iph->check = update_checksum(iph->check, before, after);

	/* swap src and dst MAC addresses */
	__u8 tmp[6];
	memcpy(tmp, eth->h_source, ETH_ALEN);
	memcpy(eth->h_source, eth->h_dest, ETH_ALEN);
	memcpy(eth->h_dest, tmp, ETH_ALEN);
}

SEC("xdp_prog")
int prog(struct xdp_md *ctx)
{
	struct bpf_sock *sock;
	struct bpf_sock_tuple tuple;

	void *data_end = (void *)(long)ctx->data_end;
	void *data = (void *)(long)ctx->data;
	struct ethhdr	*eth = data;
	struct iphdr	*iph;
	struct tcphdr	*tcp;
	int action = XDP_PASS;

	/* check eth header */
	if (data + sizeof(*eth) > data_end) {
		action = XDP_DROP;
		goto out;
	}
	if (eth->h_proto != bpf_htons(ETH_P_IP)) {
		goto out; /* we only focus on IPv4 */
	}

	/* check ipv4 header */
	iph = data + sizeof(*eth);
	if (iph + 1 > data_end) {
		action = XDP_DROP;
		goto out;
	}

	/* XXX: We only focus on TCP. */
	if (iph->protocol != IPPROTO_TCP) {
		action = XDP_PASS;
		goto out;
	}

	/* check tcp header */
	tcp = ((void *)iph) + (iph->ihl << 2);
	if (tcp > data_end || tcp + 1 > data_end) {
		action = XDP_DROP;
		goto out;
	}

	tuple.ipv4.saddr = iph->saddr;
 	tuple.ipv4.daddr = iph->daddr;
	tuple.ipv4.sport = tcp->source;
	tuple.ipv4.dport = tcp->dest;

	trace_printk("========== packet =======");
	trace_printk("  src_ip=0x%x dst_ip=0x%x",
		     tuple.ipv4.saddr, tuple.ipv4.daddr);
	trace_printk("  src_port=0x%x dst_port=0x%x",
		     tuple.ipv4.sport, tuple.ipv4.dport);
	trace_printk("  syn=%d ack=%d win=%d", tcp->syn, tcp->ack,
		     bpf_ntohs(tcp->window));
	trace_printk("  seq=%u ack_seq=%u",
		     bpf_ntohs(tcp->seq), bpf_ntohs(tcp->ack_seq));
	trace_printk("==============================");

	/* Find a corresponding TCP socket for this packet. If socket
	 * does not exist for the packet, and the packet does not have
	 * SYN flag, the packet belongs to other flow handled by other
	 * servers. Back the packet to the ECMP-ER Router!
	 */

	sock = bpf_skc_lookup_tcp(ctx, &tuple, sizeof(tuple.ipv4), -1, 0);

	if (!sock) {
		trace_printk("!sock: xfrm_for_retransmit");
		xfrm_for_retransmit(eth, iph);
		action = XDP_TX;
		goto out;
	}

	if (!sock && tcp->syn) {
		/* This is the first packet of connection */
		action = XDP_PASS;
		goto out;
	}

	trace_printk("=========== socket =========");
	if (sock) {
		//if (sock->state == BPF_TCP_LISTEN) {
		//	trace_printk("  sock->state: BPF_TCP_LISTEN");
		//}
		trace_printk("  sock->state=%d", sock->state);
		trace_printk("  src_ip=0x%x dst_ip=0x%x",
			     sock->src_ip4, sock->dst_ip4);
		trace_printk("  src_port=0x%x dst_port=0x%x",
			     sock->src_port, sock->dst_port);
	} else {
		trace_printk("no socket found");
	}
	trace_printk("==============================\n");

	if (sock && sock->state == BPF_TCP_LISTEN && !tcp->syn) {

		trace_printk("sock && sock->state == BPF_TCP_LISTEN && !tcp->syn");
		
		if (iph->tos == ECMP_ER_TOS_RETRANSMITTED) {
			/* I don't have a socket for this packet,
			 * but the packet is already retransmitted.
			 * goto send RST. */

			trace_printk("iph->tos == ECMP_ER_TOS_RETRANSMITTED");

			action = XDP_PASS;
			goto out_sk_release;
		}
		
		xfrm_for_retransmit(eth, iph);
		action = XDP_TX;
		goto out_sk_release;
	}		

out_sk_release:
	if (sock)
		bpf_sk_release(sock);

out:
	update_received_counter(ctx);
	if (action == XDP_TX)
		update_redirected_counter(ctx);

	return action;
}

char _license[] SEC("license") = "GPL";
