# Changelog - Z80 Master Commander (ZMC)

## [4.8.2] - 2026-01-30
### Corregido
- **Bug de Selección Múltiple**: Se solucionó un `AttributeError` en la función `toggle_mark` de `panel.py`. El error ocurría porque el sistema intentaba aplicar métodos de cadena a una tupla `(nombre, tamaño)`.
- **Indentación**: Corrección de bloques de código en `panel.py` para asegurar la compatibilidad con Python 3.11.

### Agregado
- **Cálculo de Tamaño Total**: Nueva funcionalidad en la barra de estado que muestra la cantidad de archivos seleccionados y la suma total de su tamaño (en K o M).
- **Soporte de Metadatos en Selección**: El motor de marcado ahora reconoce y extrae correctamente los nombres de archivos tanto en modo local como en modo DSK (CP/M).

### Mejoras de UI
- **Barra de Estado Dinámica**: Se rediseñó la penúltima línea de la interfaz para alternar entre la ruta actual y los datos de selección.
- **Visualización Estilo MC**: Mejoras en el método `draw` para mantener el separador vertical `│` incluso cuando hay archivos resaltados.
# CHANGELOG - Z80 Master Commander (ZMC)

## [v4.8.4] - 2026-01-30

### Añadido
- **Universal Diff ('D')**: Se integró la capacidad de comparar archivos mediante `mcdiff` o `vimdiff`.
- **Soporte DSK para Diff**: Ahora es posible comparar archivos que residen dentro de imágenes `.dsk` (CP/M) contra archivos locales o de otros discos mediante puentes en `TMP_DIR`.

### Mejorado
- **Interfaz "Soft Edition"**: Nuevo esquema de colores (Gris/Blanco sobre Azul) y uso de `A_BOLD` para directorios, optimizado para evitar la fatiga visual en la ThinkCentre.
- **Lógica de Creación de Discos**: El comando `New Disk ('N')` ahora utiliza la ruta dinámica del panel activo (`src.path`) en lugar del directorio de ejecución.
- **Estabilidad de Shell**: Implementación corregida de `curses.def_shell_mode()` y `curses.reset_shell_mode()` para un retorno limpio al programa tras usar herramientas externas.

### Cambiado
- **Mapeo de Teclas**: Se eliminó el conflicto entre la tecla 'E' (Edit) y el borrado. El borrado queda asignado exclusivamente a `F8` (Delete) y la tecla 'D' a la nueva función Diff.
- **Inicialización de Terminal**: Se forzó el uso de `stty sane` al cierre para garantizar la integridad de la consola tras la ejecución.

---
*Desarrollado por Volney Torres Almendro - lu1pvt*
