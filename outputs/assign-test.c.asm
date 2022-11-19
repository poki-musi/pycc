    .text
    .globl main
    .type main, @function
main:
    pushl ebp
    movl esp, ebp
    
    movl $1, eax
    cmpl $0, eax
    je .J0
    call main
.J0:
    
    movl $0, eax
    movl ebp, esp
    popl ebp
    ret
    