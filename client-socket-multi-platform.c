#if !defined(_WIN32) && (defined(__unix__) || defined(__unix) || (defined(__APPLE__) && defined(__MACH__)))
	/* UNIX-style OS. ------------------------------------------- */
#include <stdio.h>
#include <stddef.h>
#include <stdlib.h>
#include <strings.h>
#include <unistd.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/types.h>
#include <sys/socket.h>
#if defined(_AIX)
	/* IBM AIX. ------------------------------------------------- */
#include <sys/un.h>
#include <arpa/inet.h>
        /* AIX - build with XLC - command:
        $ /usr/vac/bin/xlc -qlanglvl=extc99 -q64 -O0 -g client-socket-multi-platorm.c -o client-socket-multi-platorm.out
        */
#endif

#if defined(__sun) && defined(__SVR4)
	/* Solaris. ------------------------------------------------- */
        /* Solaris - build with Solaris Studio / CC - command:
        $ /opt/solarisstudio12.4/bin/cc -o client-socket-multi-platorm.out -l socket -l nsl client-socket-multi-platorm.c
        */
#endif

#if defined(_AIX)
	/* IBM AIX. ------------------------------------------------- */
void *get_in_addr(struct sockaddr *sa)
{
    if (sa->sa_family == AF_INET) {
        return &(((struct sockaddr_in*)sa)->sin_addr);
    }

    return &(((struct sockaddr_in6*)sa)->sin6_addr);
}
#endif

int main(int argc, char *argv[])
{
   int sockfd, portno, n;
   struct sockaddr_in serv_addr;
   struct hostent *server;
   char message[100];
   char nagios_filter[50];
   char *host;
   char *check;
   char *myteam;
#if defined(_AIX)
	/* IBM AIX. ------------------------------------------------- */
   struct addrinfo *p;
   char s[INET6_ADDRSTRLEN];
   char *addr_list;
   char str[INET_ADDRSTRLEN];
   unsigned int i = 0;
#endif

   if (argc < 5) {
      fprintf(stderr,"Usage: %s hostname port check team\n", argv[0]);
      exit(2);
   }
   portno = atoi(argv[2]);

   if (argc == 5) {
   /* Create a socket point */
   sockfd = socket(AF_INET, SOCK_STREAM, 0);

   if (sockfd < 0)
   {
      perror("Error opening socket");
      exit(1);
   }

   server = gethostbyname(argv[1]);

   if (!server) {
      fprintf(stderr, "Error, no such host name %s\n", argv[1]);
      exit(2);
   }

   bzero((char *) &serv_addr, sizeof(serv_addr));
   serv_addr.sin_family = AF_INET;
   bcopy((char *)server->h_addr, (char *)&serv_addr.sin_addr.s_addr, server->h_length);
   serv_addr.sin_port = htons(portno);

#if defined(_AIX)
        /* IBM AIX. ------------------------------------------------- */
   /*printf("Official name is: %s\n", server->h_name);*/
   server=gethostbyaddr(&serv_addr, sizeof serv_addr, AF_INET);
   /*printf("    IP addresses: ");*/
   inet_ntop(p->ai_family, get_in_addr((struct sockaddr *)p->ai_addr),
            (char *)&serv_addr, sizeof serv_addr);

   inet_ntop(AF_INET, &(serv_addr.sin_addr), str, INET_ADDRSTRLEN);
   /*printf("%s\n", str);*/
#endif

   /* Now connect to the server */
   if (connect(sockfd,(struct sockaddr *)&serv_addr,sizeof(serv_addr)) < 0)
   {
      perror("ERROR connecting");
      exit(1);
   }

   /* Now generate a message to be read by the server */
   host=argv[1];
   check=argv[3];
   myteam=argv[4];
   sprintf(nagios_filter, "%s.%s", check, myteam);
   sprintf(message, "rexec XjfRlRNcTGSJQ /var/monitor-client/monitor.py --nagios_filter=%s\n", nagios_filter);
   /* Send message to the server */
   n = write(sockfd,message,strlen(message));
   char *myteam;

   if (n < 0)
   {
      perror("Error writing to socket");
      exit(1);
   }
   /* Now read server response */
   bzero(message,256);
   n = read(sockfd,message,256);

   if (n < 0)
   {
      perror("Error reading from socket");
      exit(1);
   }
   /* Get only the descrition output from the command */
   char seps[]   = "|";
   char *token;
   token = strtok( message, seps );
   int description = 0;
   while( token != NULL )
   {
      int counter = 5;
      if ( description == counter ) {
          printf( "%s\n", token );
      }
      // Get next token: 
      token = strtok( NULL, seps );
      description++;
   }
   /* ...Or get all the output from the server by removing the above. */
   /*printf("%s\n",message);*/

    return 0;
   }
}

#endif
