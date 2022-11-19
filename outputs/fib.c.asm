    .section  .rodata
.L4
    .string "%i\n"

    .text
    .globl fib
    .type fib, @function
fib:
    pushl ebp
    movl esp, ebp
    
    movl 8(%ebp), eax
    pushl eax
    movl $1, eax
    movl eax, ebx
    popl eax
    cmpl eax, ebx
    jgt .J0
    movl $1, eax
    j .J1
.J0:
    movl $0, eax
.J1:
    cmpl $0, eax
    je .J2
    movl 8(%ebp), eax
.J2:
    cmpl $0, eax
    jne .J3
    movl 8(%ebp), eax
    pushl eax
    movl $1, eax
    movl eax, ebx
    popl eax
    subl ebx, eax
    pushl eax
    call fib
    addl $4, esp
    pushl eax
    movl 8(%ebp), eax
    pushl eax
    movl $2, eax
    movl eax, ebx
    popl eax
    subl ebx, eax
    pushl eax
    call fib
    addl $4, esp
    movl eax, ebx
    popl eax
    addl ebx, eax
.J3:
    movl ebp, esp
    popl ebp
    ret
    
    movl $0, eax
    movl ebp, esp
    popl ebp
    ret
    
    .text
    .globl main
    .type main, @function
main:
    pushl ebp
    movl esp, ebp
    
    movl $10, eax
    pushl eax
    call fib
    addl $4, esp
    pushl eax
    movl $.L4, eax
    call printf
    addl $8, esp
    
    movl $0, eax
    movl ebp, esp
    popl ebp
    ret
    