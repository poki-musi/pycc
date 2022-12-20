# Cambios Para Después

Cada uno de los siguientes puntos será etiquetado con un número de estrellas (*), indicando cuánto queremos realizarlos eventualmente.

## Relacionado con el AST (***)

* Hacer que el "tipado" del AST sea más específico (hacer una subclase para
  Stmts, Exps, etc).
* Además, algunos refactors para simplificar código.

## Relacionado con `return`s (***)

* Cuando se encuentra un return en un bloque de código, se tiene que lanzar
  un warning si hay aun más código despúes del return, y declarar que es
  código muerto.
* Además, código después del return debe de ser ignorado, no compilado (esto
  permite no emitir un return implícito al final de las funciones, lo cual
  está guay).
* Además además, una función no void debe siempre de devolver un valor, toca
  verificar todos los caminos por un return.

## Refactorizar `scanf`/`printf` (***)

Básicamente deberían de crear un nodo llamado `VariadicCallEx` en vez de un nodo
especial `Scanf`/`Printf`. Éste contiene la signatura de los tipos esperados por
lso argumentos de la llamada. Ejemplo:

```c
scanf("%i %i", &a, &b);
```

Debería de generar un nodo `VariadicCallExp` tal que:

```python
sig = # (char*, int*, int*) -> void
VariadicCallExp(name="scanf", sig=sig, args=...)
```

## Mejor parsing para `if`s (**)

Quizás el `if` debería de aceptar statements anidados sin llaves (baja
  prioridad).

```c
int fun() {
  if(x)
    if(y)
      something();
  else
    something();
}
```

## Mejor generación de errores (**)

Después de optimizar todo lo que queramos mejorar, estaría bien mejorar el
sistema de errores. En estos momentos, lanzan error immediatemente y terminan
completamente. Estaría mejor que pudieran "recuperarse" y seguir buscando
errores.

### Resolver (**)

### Parser (*)

sly es un coñazo y lo odio. La menor prioridad para mejor generador de errores.

## Limpieza de condicionales (*)

En estos momentos, código como:

```c
int main() {
  int x = 1 && 3 + 4;
}
```

Es válido, y genera asm muy feo para convertir un booleano a un entero (también
ocurre esto al asignar valores).
Para evitar este problema, estaría bien:

* Admitir tipos booleanos (eventualmente).
* Sólo convertir entre el valor de la flag adecuada a un valor de registro
  cuando sea necesario.
  * Al asignar la flag a una variable.
  * Al convertirlo implícitamente a un entero.

## Admitir tipos de vectores y punteros nestados (*)

En estos momentos, declaraciones como:

```c
int* (*a[3])[3];
```

No son válidos (aunque no deberían de haberlo sido en C tbh...). Si
eventualmente aceptamos estos tipos de valores, tenemos que:

* Cambiar el parsing para aceptar arrays nestados, lo que significa cambiar
  completamente cómo se parsean identificadores en declaraciones y en
  parámetros de funciones.
* Esto eventualmente implica tener que copiar arrays a los argumentos de una
  llamada a una función, lo que significa que no tenemos movimientos triviales
  (es decir, mover un valor de 32 bits a la stack como hemos estado haciendo
  hasta ahora).
