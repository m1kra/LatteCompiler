#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern void printInt(int n){
	printf("%d\n", n);
}

extern void printString(char* s){
	printf("%s\n", s);
}

extern int readInt(){
	int n;
	scanf("%d", &n);
	getchar();
	return n;
}

extern char *readString(){
    char* line = NULL;
    size_t len = 0;
    int nread = getline(&line, &len, stdin);
    if (nread == -1){
        exit(1);
    }
    if (line[nread - 1] == '\n'){
        line[nread - 1] = '\0';
    }
    return line;
}

extern void error(){
	exit(1);
}

extern char* _concat(char* l, char* r){
	char* res = malloc(strlen(l) + strlen(r) + 1);
	strcpy(res, l);
	strcat(res, r);
	return res;
}

extern int _str_equal(char* l, char* r){
	if (strcmp(l, r) == 0)
		return 1;
	return 0;
}

extern int* _malloc(int size){
	return calloc(size, 1);
}