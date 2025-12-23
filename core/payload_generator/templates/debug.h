
#pragma once

#include <windows.h>

#ifdef DEBUG

#define PRINTA(STR, ...)                                                       \
  do {                                                                         \
    LPSTR buf = (LPSTR)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, 1024);    \
    if (buf) {                                                                 \
      /* the '##' swallows the comma if no args */                             \
      int len = wsprintfA(buf, STR, ##__VA_ARGS__);                            \
      WriteConsoleA(GetStdHandle(STD_OUTPUT_HANDLE), buf, len, NULL, NULL);    \
      HeapFree(GetProcessHeap(), 0, buf);                                      \
    }                                                                          \
  } while (0)

#else
#define PRINTA(STR, ...)                                                       \
  do {                                                                         \
  } while (0)
#endif
