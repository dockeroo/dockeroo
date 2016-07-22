#define _POSIX_SOURCE
#include <signal.h>
#include <stdlib.h>

void catcher(int signum) {
    exit(0);
}

main() {
    sigset_t         set;
    struct sigaction act;

    sigemptyset(&act.sa_mask);
    act.sa_flags   = 0;
    act.sa_handler = catcher;

    if (sigaction(SIGINT,  &act, NULL) != 0 ||
        sigaction(SIGTERM, &act, NULL) != 0) {
        exit(1);
    }

    sigemptyset(&set);

    if (sigsuspend(&set) == -1) {
        exit(0);
    }
}
