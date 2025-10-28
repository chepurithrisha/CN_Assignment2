#define _POSIX_C_SOURCE 200809L
#include<stdio.h>
#include<stdlib.h>
#include<string.h>
#include<time.h>
#include<sys/time.h>
#include<netdb.h>
#include<unistd.h>
#include<errno.h>

static double timespec_to_ms(const struct timespec *ts){
    return ts->tv_sec*1000.0+ts->tv_nsec/1e6;
}

static double elapsed_ms(const struct timespec *start,const struct timespec *end){
    double s=timespec_to_ms(start);
    double e=timespec_to_ms(end);
    return e-s;
}

int main(int argc,char **argv){
    if (argc!=2){
        fprintf(stderr,"Usage: %s hostnames.txt\n",argv[0]);
        return 1;
    }

    const char *fname=argv[1];
    FILE *f=fopen(fname,"r");
    if (!f){
        perror("fopen");
        return 1;
    }

    char buf[1024];
    unsigned long total_count=0,success_count=0,fail_count=0;
    double sum_latency_ms=0.0;
    struct timespec t_start_all,t_end_all;
    clock_gettime(CLOCK_MONOTONIC,&t_start_all);

    printf("hostname,latency_ms,result,errstr\n");

    while(fgets(buf,sizeof(buf),f)){
        char *p=buf;
        while(*p&&(*p==' '||*p=='\t'))p++;
        char *q=p+strlen(p)-1;
        while(q>=p&&(*q=='\n'||*q=='\r'||*q==' '||*q=='\t')){
            *q='\0';
            q--; 
        }
        if(strlen(p)==0) continue;

        total_count++;
        struct timespec t1,t2;
        clock_gettime(CLOCK_MONOTONIC,&t1);

        struct addrinfo hints;
        struct addrinfo *res=NULL;
        memset(&hints,0,sizeof(hints));
        hints.ai_family=AF_UNSPEC;
        hints.ai_socktype=SOCK_STREAM;

        int err=getaddrinfo(p,NULL,&hints,&res);

        clock_gettime(CLOCK_MONOTONIC,&t2);
        double ms=elapsed_ms(&t1,&t2);

        if(err == 0&&res){
            success_count++;
            sum_latency_ms+=ms;
            printf("%s,%.3f,OK,\n",p,ms);
            freeaddrinfo(res);
        } else {
            fail_count++;
            sum_latency_ms+=ms;
            const char *estr=gai_strerror(err);
            printf("%s,%.3f,FAIL,%s\n",p,ms,estr?estr:strerror(errno));
        }
    }

    clock_gettime(CLOCK_MONOTONIC,&t_end_all);
    double total_time_sec=(timespec_to_ms(&t_end_all)-timespec_to_ms(&t_start_all)) / 1000.0;

    double avg_latency_ms=(total_count > 0) ? (sum_latency_ms/total_count) : 0.0;
    double success_throughput=(total_time_sec>0.0) ? (double)success_count/total_time_sec : 0.0;

    fprintf(stderr,"\nSUMMARY\n");
    fprintf(stderr,"Total queries: %lu\n",total_count);
    fprintf(stderr,"Success: %lu\n",success_count);
    fprintf(stderr,"Fail: %lu\n",fail_count);
    fprintf(stderr,"Total elapsed time (s): %.4f\n",total_time_sec);
    fprintf(stderr,"Average latency per query (ms) (incl failures): %.3f\n",avg_latency_ms);
    fprintf(stderr,"Throughput (successful resolutions/sec): %.3f\n",success_throughput);

    fclose(f);
    return 0;
}

