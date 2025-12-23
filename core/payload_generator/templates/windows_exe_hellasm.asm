
; -- Data section ------------------------------------------------------------
section .data

TakeAllTrilliare:   dd 0

; -- Code section ------------------------------------------------------------
section .text
    global TheDogHouse
TheDogHouse:
    ; clear the flag first
    mov dword [rel TakeAllTrilliare], 0
    ; then store RCX into it (low 32 bits only)
    mov dword [rel TakeAllTrilliare], ecx
    ret

    global TheFlagOfWudan
TheFlagOfWudan:
    mov r10, rcx               
    mov eax, dword [rel TakeAllTrilliare]
    syscall
    ret
