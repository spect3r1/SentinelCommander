
#include <windows.h>

#include "common.h"
#include "structs.h"
#include <intrin.h>

#ifndef BUILD_SEED
#define BUILD_SEED 0xC0FFEE42
#endif

static inline WORD make_dos_sig(void) {
  const WORD A = 0xA1B2;
  const WORD B = (WORD)(A ^ 0x5A4D);
  return (WORD)(A ^ B);
}

static inline DWORD make_nt_sig(void) {
  const DWORD X = 0x11223344;
  const DWORD Y = X ^ 0x00004550;
  return (DWORD)(X ^ Y);
}

FARPROC GetProcAddressH(HMODULE hModule, DWORD dwApiNameHash) {

  if (hModule == NULL || dwApiNameHash == NULL)
    return NULL;

  PBYTE pBase = (PBYTE)hModule;

  PIMAGE_DOS_HEADER pImgDosHdr = (PIMAGE_DOS_HEADER)pBase;
  if (pImgDosHdr->e_magic != make_dos_sig())
    return NULL;

  PIMAGE_NT_HEADERS pImgNtHdrs =
      (PIMAGE_NT_HEADERS)(pBase + pImgDosHdr->e_lfanew);
  if (pImgNtHdrs->Signature != make_nt_sig())
    return NULL;

  IMAGE_OPTIONAL_HEADER ImgOptHdr = pImgNtHdrs->OptionalHeader;

  IMAGE_EXPORT_DIRECTORY *exp =
      (PIMAGE_EXPORT_DIRECTORY)(pBase +
                                ImgOptHdr
                                    .DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT]
                                    .VirtualAddress);
  PDWORD names = (PDWORD)(pBase + exp->AddressOfNames);
  PWORD ordinals = (PWORD)(pBase + exp->AddressOfNameOrdinals);
  PDWORD funcs = (PDWORD)(pBase + exp->AddressOfFunctions);
  DWORD count = exp->NumberOfNames;

  DWORD stride = ((BUILD_SEED >> 8) ^ (BUILD_SEED & 0xFF)) | 1;

  for (DWORD pass = 0, idx = 0; pass < count;
       pass++, idx = (idx + stride) % count) {
    if (((pass ^ BUILD_SEED) & 3) == 0) {
      __nop();
      __nop();
    }

    CHAR *pFunctionName = (CHAR *)(pBase + names[idx]);
    DWORD mangledHash = HASHA(pFunctionName) ^ (BUILD_SEED >> 16);
    DWORD targetMangled = dwApiNameHash ^ (BUILD_SEED >> 16);
    if (mangledHash == targetMangled) {
      __nop();
      return (FARPROC)(pBase + funcs[ordinals[idx]]);
    }
  }

  return NULL;
}

HMODULE GetModuleHandleH(DWORD dwModuleNameHash) {

  if (dwModuleNameHash == NULL)
    return NULL;

#ifdef _WIN64
  PPEB pPeb = (PEB *)(__readgsqword(0x60));
#elif _WIN32
  PPEB pPeb = (PEB *)(__readfsdword(0x30));
#endif

  PPEB_LDR_DATA pLdr = (PPEB_LDR_DATA)(pPeb->Ldr);
  PLDR_DATA_TABLE_ENTRY pDte =
      (PLDR_DATA_TABLE_ENTRY)(pLdr->InMemoryOrderModuleList.Flink);

  while (pDte) {

    if (pDte->FullDllName.Length != NULL &&
        pDte->FullDllName.Length < MAX_PATH) {

      CHAR UpperCaseDllName[MAX_PATH];

      DWORD i = 0;
      while (pDte->FullDllName.Buffer[i]) {
        UpperCaseDllName[i] = (CHAR)_toUpper(pDte->FullDllName.Buffer[i]);
        i++;
      }
      UpperCaseDllName[i] = '\0';

      if (HASHA(UpperCaseDllName) == dwModuleNameHash)
        return (HMODULE)(pDte->InInitializationOrderLinks.Flink);

    } else {
      break;
    }

    pDte = *(PLDR_DATA_TABLE_ENTRY *)(pDte);
  }

  return NULL;
}
