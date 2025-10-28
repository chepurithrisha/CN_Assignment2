#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/time.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <errno.h>

const char *root_servers[] = {
    "198.41.0.4", "199.9.14.201", "192.33.4.12", "199.7.91.13", "192.203.230.10"
};
#define ROOT_SERVER_COUNT 5

struct dnshdr {
    unsigned short id, flags, qdcount, ancount, nscount, arcount;
};
int make_dns_query(const char* hostname, unsigned char* buf) {
    memset(buf, 0, 512);
    struct dnshdr *hdr = (struct dnshdr *)buf;
    hdr->id = htons(0x1234);
    hdr->flags = htons(0x0100); // standard query
    hdr->qdcount = htons(1);
    int offs = sizeof(struct dnshdr);
    const char *p = hostname;
    while (*p) {
        const char *dot = strchr(p, '.');
        if (!dot) dot = p + strlen(p);
        int len = dot - p;
        buf[offs++] = len;
        memcpy(buf + offs, p, len);
        offs += len;
        p += len;
        if (*p == '.') ++p;
    }
    buf[offs++] = 0;
    buf[offs++] = 0; buf[offs++] = 1;
    buf[offs++] = 0; buf[offs++] = 1;
    return offs;
}
void parse_dns_response(const unsigned char* buf, ssize_t len, char* result_type, size_t result_len, char* response_info, size_t info_len) {
    if (len < sizeof(struct dnshdr)) {
        snprintf(result_type, result_len, "Error");
        snprintf(response_info, info_len, "Short response");
        return;
    }
    const struct dnshdr *hdr = (const struct dnshdr *)buf;
    int ancount = ntohs(hdr->ancount);
    int nscount = ntohs(hdr->nscount);
    int rcode = ntohs(hdr->flags) & 0xf;
    if (rcode != 0) {
        snprintf(result_type, result_len, "Error");
        snprintf(response_info, info_len, "RCODE %d", rcode);
    } else if (ancount > 0) {
        snprintf(result_type, result_len, "Answer");
        snprintf(response_info, info_len, "%d answer(s)", ancount);
    } else if (nscount > 0) {
        snprintf(result_type, result_len, "Referral");
        snprintf(response_info, info_len, "%d NS (authority) record(s)", nscount);
    } else {
        snprintf(result_type, result_len, "Empty");
        snprintf(response_info, info_len, "-");
    }
}
void log_csv(const char* timestamp, const char* domain, const char* mode,
    const char* dns_ip, const char* step, const char* result_type,
    double rtt, double total_t, const char* cache_status, const char* response_info) {
    printf("%s,%s,%s,%s,%s,%s,%.3f,%.3f,%s,%s\n",
        timestamp, domain, mode, dns_ip, step, result_type, rtt, total_t, cache_status, response_info);
}
int send_query(const char *dns_ip, int port, unsigned char* query_buf, int query_len, unsigned char* response_buf, ssize_t *resp_len, double *rtt_ms) {
    struct timeval t1, t2;
    gettimeofday(&t1, NULL);
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    inet_pton(AF_INET, dns_ip, &(addr.sin_addr));
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    sendto(sock, query_buf, query_len, 0, (struct sockaddr *)&addr, sizeof(addr));
    socklen_t addr_len = sizeof(addr);
    *resp_len = recvfrom(sock, response_buf, 512, 0, (struct sockaddr *)&addr, &addr_len);
    close(sock);
    gettimeofday(&t2, NULL);
    *rtt_ms = (t2.tv_sec - t1.tv_sec) * 1000.0 + (t2.tv_usec - t1.tv_usec) / 1000.0;
    return 0;
}
int main(int argc, char **argv) {
    if (argc != 2) { fprintf(stderr, "Usage: %s domain\n", argv[0]); return 1; }
    const char *domain = argv[1];
    struct timeval tv_all_start, tv_all_end;
    gettimeofday(&tv_all_start, NULL);
    char timestamp[64];
    time_t now = time(NULL);
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", localtime(&now));
    char mode[] = "UDP";
    char cache_status[] = "UNKNOWN";
    printf("timestamp,domain,mode,dns_ip,step,result_type,round_trip_ms,total_ms,cache_status,response_info\n");
    int port = 53;
    unsigned char query_buf[512], response_buf[512];
    int query_len = make_dns_query(domain, query_buf);
    //--- Root Step ---
    const char *current_servers[16]; int ns_count = 0;
    for (int i = 0; i < ROOT_SERVER_COUNT; ++i) current_servers[ns_count++] = root_servers[i];
    const char *step = "root";
    while (ns_count > 0) {
        for (int sidx = 0; sidx < ns_count; ++sidx) {
            double rtt = 0.0;
            ssize_t resp_len = 0;
            send_query(current_servers[sidx], port, query_buf, query_len, response_buf, &resp_len, &rtt);
            gettimeofday(&tv_all_end, NULL);
            double total_t = (tv_all_end.tv_sec - tv_all_start.tv_sec) * 1000.0 + (tv_all_end.tv_usec - tv_all_start.tv_usec) / 1000.0;
            char result_type[32], response_info[128];
            parse_dns_response(response_buf, resp_len, result_type, sizeof(result_type), response_info, sizeof(response_info));
            log_csv(timestamp, domain, mode, current_servers[sidx], step, result_type, rtt, total_t, cache_status, response_info);
            // If answer, done!
            if (strcmp(result_type, "Answer") == 0) return 0;
            // If referral, extract NS IPs from additional section (nontrivial in plain C: mock TLD here for brevity)
            if (strcmp(result_type, "Referral") == 0) {
                // For demonstration, parse TLD servers from mock known list (replace with extract from response for real code!)
                static const char *com_tld[] = {"192.5.6.30", "192.35.51.30", "192.42.93.30"}; // Example TLDs for .com
                ns_count = 3;
                memcpy(current_servers, com_tld, sizeof(com_tld));
                step = "tld";
                break;
            }
        }
        if (strcmp(step, "tld") == 0) {
            // Next: simulate single "auth" step to domain's authoritative nameserver
            static const char *google_ns[] = {"216.239.32.10"}; // Example: authoritative
            ns_count = 1;
            memcpy(current_servers, google_ns, sizeof(google_ns[0]));
            step = "auth";
        } else if (strcmp(step, "auth") == 0) break;
    }
    return 0;
}