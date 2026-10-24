/* Ed25519 verification one signature at a time against batch verification (OPEN_ITEMS G19).
 *
 * The receiver-CPU ceiling of docs/02 §6c charges one verification per frame. Ed25519 was
 * designed for batch verification, which the library this project is built on does not expose.
 * This times both in one library that has it (ed25519-donna, public domain), so the figure that
 * matters -- the RATIO on a given board -- is measured and not quoted.
 *
 *   ./bench_batch [repetitions]      prints CSV: batch,median_ns_per_sig,min_ns,max_ns,reps
 *
 * batch = 1 is ed25519_sign_open; larger values are ed25519_sign_open_batch over 64 distinct
 * keys, messages and signatures (200 B messages, as in the P1 crypto timings). Every signature
 * is checked to verify in every repetition; a failure aborts.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "ed25519.h"

#define MSG 200
#define NSIG 64

/* The library asks the application for randomness for the batch coefficients. */
void ed25519_randombytes_unsafe(void *p, size_t len) {
    FILE *f = fopen("/dev/urandom", "rb");
    if (!f || fread(p, 1, len, f) != len) { fprintf(stderr, "no /dev/urandom\n"); exit(2); }
    fclose(f);
}

static uint64_t now_ns(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * 1000000000ull + (uint64_t)t.tv_nsec;
}

static int by_value(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return (x > y) - (x < y);
}

static void report(int batch, double *samples, int reps) {
    qsort(samples, (size_t)reps, sizeof *samples, by_value);
    printf("%d,%.1f,%.1f,%.1f,%d\n", batch, samples[reps / 2], samples[0], samples[reps - 1], reps);
}

int main(int argc, char **argv) {
    int reps = argc > 1 ? atoi(argv[1]) : 300;
    static unsigned char sk[NSIG][32], pk[NSIG][32], msg[NSIG][MSG], sig[NSIG][64];
    const unsigned char *mp[NSIG], *pkp[NSIG], *sigp[NSIG];
    size_t ml[NSIG];
    int valid[NSIG];
    uint32_t state = 20261008u;                 /* fixed content: the same inputs on every board */
    double *samples = malloc(sizeof *samples * (size_t)reps);
    static const int sizes[] = {4, 8, 16, 32, 64};

    if (reps < 11 || !samples) { fprintf(stderr, "need at least 11 repetitions\n"); return 2; }
    for (int i = 0; i < NSIG; i++) {
        for (int j = 0; j < 32; j++) { state = state * 1664525u + 1013904223u; sk[i][j] = (unsigned char)(state >> 24); }
        for (int j = 0; j < MSG; j++) { state = state * 1664525u + 1013904223u; msg[i][j] = (unsigned char)(state >> 24); }
        ed25519_publickey(sk[i], pk[i]);
        ed25519_sign(msg[i], MSG, sk[i], pk[i], sig[i]);
        mp[i] = msg[i]; pkp[i] = pk[i]; sigp[i] = sig[i]; ml[i] = MSG;
    }
    for (int warm = 0; warm < 20; warm++)       /* caches and frequency governor settle */
        for (int i = 0; i < NSIG; i++) (void)ed25519_sign_open(msg[i], MSG, pk[i], sig[i]);

    printf("batch,median_ns_per_sig,min_ns,max_ns,reps\n");
    for (int r = 0; r < reps; r++) {
        uint64_t t0 = now_ns();
        int bad = 0;
        for (int i = 0; i < NSIG; i++) bad |= ed25519_sign_open(msg[i], MSG, pk[i], sig[i]);
        samples[r] = (double)(now_ns() - t0) / NSIG;
        if (bad) { fprintf(stderr, "a valid signature failed (single)\n"); return 1; }
    }
    report(1, samples, reps);
    for (size_t s = 0; s < sizeof sizes / sizeof *sizes; s++) {
        int b = sizes[s];
        for (int r = 0; r < reps; r++) {
            uint64_t t0 = now_ns();
            int bad = 0;
            for (int at = 0; at + b <= NSIG; at += b)
                bad |= ed25519_sign_open_batch(mp + at, ml + at, pkp + at, sigp + at, (size_t)b, valid + at);
            samples[r] = (double)(now_ns() - t0) / NSIG;
            if (bad) { fprintf(stderr, "a valid signature failed (batch %d)\n", b); return 1; }
        }
        report(b, samples, reps);
    }
    free(samples);
    return 0;
}
