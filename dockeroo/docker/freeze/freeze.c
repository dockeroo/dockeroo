
/*
 * -*- coding: utf-8 -*-
 * 
 * Copyright (c) 2016, Giacomo Cariello. All rights reserved.
 * 
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *   http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */


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
