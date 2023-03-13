obj := .
src := .


DEBUGBPF = -DDEBUG
#DEBUGBPF = -DDEBUG -DREDIRECT_DEBUG
DEBUGFLAGS = -O0 -Wall
PFLAGS = $(DEBUGFLAGS)

INCLUDEFLAGS = -I$(obj)/include



#always = src/example.o
always = redirect.o er-stat
# always += src/a.o
tests = test/test_xdp.o

HOSTCFLAGS += $(INCLUDEFLAGS) $(PFLAGS)
HOSTCFLAGS_bpf_load.o += $(INCLUDEFLAGS) $(PFLAGS) -Wno-unused-variable


# Allows pointing LLC/CLANG to a LLVM backend with bpf support, redefine on cmdline:
#  make samples/bpf/ LLC=~/git/llvm/build/bin/llc CLANG=~/git/llvm/build/bin/clang
LLC ?= llc
CLANG ?= clang
CC ?= gcc

LIBS = -l:libbpf.a -lelf $(USER_LIBS)

# Trick to allow make to be run from this directory
all: $(always)
	$(MAKE) -C .. $$PWD/
	
clean:
	@rm $(always)

test: $(tests)
	$(MAKE) -C .. $$PWD/
	sudo $<

$(obj)/%.o: $(src)/%.c
	$(CLANG) $(INCLUDEFLAGS) $(EXTRA_CFLAGS) \
	$(DEBUGBPF) -D__KERNEL__ -Wno-unused-value -Wno-pointer-sign \
		-Wno-compare-distinct-pointer-types \
		-O2 -emit-llvm -c -g $< -o -| $(LLC) -march=bpf -filetype=obj -o $@

$(obj)/test/%.o: $(src)/test/%.c
	$(CC) -Wall $(INCLUDEFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ $< $(LIBS)

er-stat: er-stat.c
	$(CC) -g -Wall $^ -lbcc -lbpf -o $@

install: er-stat
	sudo install -m 755 er-stat /usr/local/bin/
