import curses
import os
import subprocess
import shutil
from config import VISOR, EDITOR, TMP_DIR
from panel import Panel
from operations import launch_tool, file_op, delete_op
# En la parte de arriba de zmc.py
from operations import get_available_formats, show_selection_menu  # <--- Asegurate de que estén ambas
def show_welcome(stdscr):
    """Pantalla de bienvenida restaurada"""
    h, w = stdscr.getmaxyx()
    stdscr.clear()
    banner = [
        "███████╗███╗   ███╗ ██████╗ ",
        "╚══███╔╝████╗ ████║██╔════╝ ",
        "  ███╔╝ ██╔████╔██║██║      ",
        " ███╔╝  ██║╚██╔╝██║██║      ",
        "███████╗██║ ╚═╝ ██║╚██████╗ ",
        "╚══════╝╚═╝     ╚═╝ ╚═════╝ ",
        "  Z80 Master Commander v4.8 ",
        "   Volney Torres Almendro   "
    ]
    try:
        for i, line in enumerate(banner):
            stdscr.addstr(h//2 - 5 + i, (w - len(line))//2, line, curses.A_BOLD)
        stdscr.addstr(h//2 + 4, (w - 30)//2, "Presioná una tecla para entrar...")
        stdscr.refresh()
        stdscr.getch()
    except: pass
def launch_diff(stdscr, p_izq, p_der, p_act):
    src = p_izq if p_act == 0 else p_der
    dst = p_der if p_act == 0 else p_izq

    if not src.files or not dst.files: return

    f1_item = src.files[src.selected_idx]
    f2_item = dst.files[dst.selected_idx]
    
    f1 = f1_item[0] if isinstance(f1_item, tuple) else f1_item
    f2 = f2_item[0] if isinstance(f2_item, tuple) else f2_item

    if f1 == ".." or f2 == "..": return

    # --- Lógica de Extracción Temporal (Puente) ---
    bridge1 = os.path.join(TMP_DIR, f"diff_src_{f1}")
    bridge2 = os.path.join(TMP_DIR, f"diff_dst_{f2}")

    try:
        # Extraemos el archivo del panel origen
        if src.is_dsk_mode:
            subprocess.run(["cpmcp", "-f", src.format, src.dsk_path, f"{src.user_area}:{f1}", bridge1], check=True)
        else:
            shutil.copy2(os.path.join(src.path, f1), bridge1)

        # Extraemos el archivo del panel destino
        if dst.is_dsk_mode:
            subprocess.run(["cpmcp", "-f", dst.format, dst.dsk_path, f"{dst.user_area}:{f2}", bridge2], check=True)
        else:
            shutil.copy2(os.path.join(dst.path, f2), bridge2)

        # Lanzamos la comparación sobre los archivos temporales
        curses.def_shell_mode()
        stdscr.clear()
        os.system(f"mcdiff '{bridge1}' '{bridge2}' || vimdiff '{bridge1}' '{bridge2}'")
        curses.reset_shell_mode()
        stdscr.refresh()

    except Exception as e:
        stdscr.addstr(h-2, 0, f" Error Diff: {str(e)[:w-15]} ".ljust(w-1), curses.A_REVERSE)
        stdscr.getch()
    finally:
        # Limpieza de los puentes
        if os.path.exists(bridge1): os.remove(bridge1)
        if os.path.exists(bridge2): os.remove(bridge2)

def draw_panel(win, p, active):
    win.erase()
    # 1. Fondo azul para todo el panel
    win.bkgd(' ', curses.color_pair(1))
    win.box()
    h, w = win.getmaxyx()

    # --- Títulos y Formato ---
    status = f"[{p.format} U{p.user_area}]"
    title = f" {os.path.basename(p.path if not p.is_dsk_mode else p.dsk_path)} "
    win.addstr(0, 2, title[:w-len(status)-4], curses.A_BOLD)
    win.addstr(0, w-len(status)-2, status, curses.A_BOLD)

    for i in range(h - 2):
        idx = p.top_idx + i
        if idx < len(p.files):
            f_item = p.files[idx]
            name, size = f_item if isinstance(f_item, tuple) else (f_item, "")

            # GEOMETRÍA MC original preservada
            ancho_interno = w - 2
            ancho_size = 7
            ancho_nombre = ancho_interno - ancho_size - 1

            # Definimos los atributos según el tipo de archivo y si está marcado
            is_dir = "DIR" in size or name == ".."
            
            # Color base: Amarillo para carpetas, Blanco para archivos
            attr_item = curses.color_pair(2) if is_dir else curses.color_pair(1)
            
            # Si está marcado, usamos el color de selección (Negro/Cian)
            if idx in p.marked_indices:
                attr_item = curses.color_pair(3)

            if idx == p.selected_idx and active:
                # Línea completa para el cursor
                linea_full = f"{name[:ancho_nombre]:<{ancho_nombre}}│{size:>{ancho_size}}"
                win.attron(curses.color_pair(3))
                win.addstr(i+1, 1, linea_full[:ancho_interno])
                win.attroff(curses.color_pair(3))
            else:
                # Dibujo por secciones respetando tus colores
                # 1. Nombre
                win.addstr(i+1, 1, f"{name[:ancho_nombre]:<{ancho_nombre}}", attr_item)
                # 2. Separador (siempre en blanco/azul para que no distraiga)
                win.addstr(i+1, 1 + ancho_nombre, "│", curses.color_pair(1))
                # 3. Tamaño
                win.addstr(i+1, 1 + ancho_nombre + 1, f"{size:>{ancho_size}}", attr_item)
                
    win.refresh()

def main(stdscr):
    # 1. Forzamos la configuración de la terminal antes de empezar
    os.environ.setdefault('TERM', 'xterm-256color')
    
    # 2. Inicialización de curses
    curses.noecho()          # No muestra los códigos ^[OB al presionar flechas
    curses.cbreak()          # Lee las teclas al instante
    stdscr.keypad(True)      # TRADUCE las secuencias ^[OB a curses.KEY_DOWN
    curses.curs_set(0)       # Oculta el cursor
    
    # 3. Limpieza inicial
    stdscr.clear()
    stdscr.refresh()
    # Inicialización de colores y entrada
    #curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)  # Nombres/Marcados
    #curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK) # Tamaños y Separador
    #curses.start_color()
    #curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    # 1. Definimos los colores clásicos del MC
    curses.start_color()
    # Par 1: Blanco sobre Azul (Fondo general y archivos)
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
    # Par 2: Amarillo sobre Azul (Directorios)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)
    # Par 3: Negro sobre Cian (Barra de selección / Cursor)
    curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_CYAN)
    # Par 4: Blanco sobre Negro o Gris (Barras de estado y teclas F)
    curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLACK)

    # 2. Pintamos el fondo de la pantalla principal de Azul
    stdscr.bkgd(' ', curses.color_pair(1))
    
    os.environ.setdefault('ESCDELAY', '25')
    
    stdscr.keypad(True)
    curses.curs_set(0)
    curses.noecho()
    
    show_welcome(stdscr) # <--- ¡Bienvenida llamada correctamente!
    p_izq, p_der = Panel("."), Panel(".")
    p_act = 0
    
    while True:
        h, w = stdscr.getmaxyx()
        
        # 1. Definimos src y dst AL PRINCIPIO del bucle
        src, dst = (p_izq, p_der) if p_act == 0 else (p_der, p_izq)
        h, w = stdscr.getmaxyx()
        win_i = curses.newwin(h-2, w//2, 0, 0)
        win_d = curses.newwin(h-2, w//2, 0, w//2)
        win_i.keypad(True)
        win_d.keypad(True)
        
        draw_panel(win_i, p_izq, p_act == 0)
        draw_panel(win_d, p_der, p_act == 1)
        # --- NUEVA LÓGICA DE SUMA DE SELECCIÓN ---
        num_marcados = len(src.marked_indices)
        if num_marcados > 0:
            bytes_totales = src.get_marked_size()
            # Usamos tu función format_size del panel para que quede prolijo
            peso_str = src.format_size(bytes_totales)
            status_line = f" Seleccionados: {num_marcados} archivo(s) ({peso_str}) "
        else:
            # Si no hay nada marcado, mostramos la ruta actual como siempre
            ruta = src.path if not src.is_dsk_mode else src.dsk_path
            status_line = f" {ruta} "

        # Dibujamos la barra de estado (fila H-2, arriba de las F-keys)
        stdscr.attron(curses.A_REVERSE | curses.color_pair(2))
        stdscr.addstr(h-2, 0, status_line.ljust(w-1))
        stdscr.attroff(curses.A_REVERSE | curses.color_pair(2))

        # Tu línea de teclas F original actualizada
        msg = "F1:Sed|F2:Ren|F3:Ver|F4:Edit|F5:Copy|F6:Move|F8:delete|D:Diff|F9:Fmt|N:New"
        stdscr.addstr(h-1, 0, msg.ljust(w-1), curses.A_REVERSE)
        stdscr.refresh()
        
        k = stdscr.getch()
        src, dst = (p_izq, p_der) if p_act == 0 else (p_der, p_izq)
        # NUEVAS FUNCIONALIDADES
        
        # Tecla F1 o 's' para FSED (Editor de sectores)
        if k in [curses.KEY_F1, ord('s'), ord('S')]:
            from operations import launch_fsed
            launch_fsed(stdscr, src)
            
        # Shift + F (o podrías usar otra combinación) para Formatear Disco
        elif k in [ord('f'), ord('F')]: # 'F' mayúscula para formatear el disco físico
            from operations import format_disk_op
            format_disk_op(stdscr, src)

        if k == ord('\t'): p_act = 1 - p_act
        elif k == curses.KEY_UP and src.selected_idx > 0:
            src.selected_idx -= 1
            if src.selected_idx < src.top_idx: src.top_idx -= 1
        elif k == curses.KEY_DOWN and src.selected_idx < len(src.files) - 1:
            src.selected_idx += 1
            if src.selected_idx >= src.top_idx + (h-4): src.top_idx += 1
        elif k == 10: # ENTER
            src.action(stdscr)
        
        elif k in [curses.KEY_IC, ord(' '), 331]: # Soporte extra para INSERT
            src.toggle_mark()
            
        # --- VER (F3) ---
        elif k in [curses.KEY_F3, ord('v'), ord('V')]:
            launch_tool(stdscr, src, VISOR)

        # --- EDITAR (F4) ---
        elif k in [curses.KEY_F4, ord('e'), ord('E')]:
            launch_tool(stdscr, src, EDITOR)
            
        elif k in [curses.KEY_F5, ord('c'), ord('C')]:
            # Agregamos 'stdscr' al final para habilitar la pregunta de sobreescritura
            res = file_op(src, dst, "COPY", stdscr)
            if res: # Si hay un error, lo mostramos
                stdscr.attron(curses.A_REVERSE | curses.color_pair(1))
                stdscr.addstr(h-2, 0, f" ERROR: {res[:w-10]} ".ljust(w-1))
                stdscr.attroff(curses.A_REVERSE | curses.color_pair(1))
                stdscr.getch() # Esperamos una tecla para que el usuario lo vea

        elif k in [curses.KEY_F6, ord('m'), ord('M')]:
            # También pasamos 'stdscr' aquí para el movimiento seguro
            res = file_op(src, dst, "MOVE", stdscr)
            if res: # Si la función devuelve un error
                stdscr.attron(curses.A_REVERSE | curses.color_pair(1))
                stdscr.addstr(h-2, 0, f" ERROR: {res[:w-10]} ".ljust(w-1))
                stdscr.attroff(curses.A_REVERSE | curses.color_pair(1))
                stdscr.getch() # Pausa para que el usuario lea qué falló
            
        elif k == curses.KEY_F8:
            files = src.get_marked_files()
            stdscr.addstr(h-2, 0, f" ¿Borrar {len(files)} items? (S/N): ".ljust(w-1), curses.A_REVERSE)
            conf = stdscr.getch()
            if conf in [ord('s'), ord('S')]:
                delete_op(src)
            stdscr.addstr(h-2, 0, " ".ljust(w-1))
        elif k == curses.KEY_F9:
            formats = get_available_formats()
            chosen = show_selection_menu(stdscr, formats, "Disk Formats")
            if chosen:
                # Usamos p_izq y p_der que son tus variables en zmc.py
                # Usamos .refresh() que es el método real en panel.py
                if p_izq.is_dsk_mode:
                    p_izq.format = chosen
                    p_izq.refresh() 
                if p_der.is_dsk_mode:
                    p_der.format = chosen
                    p_der.refresh()
        # --- Navegación ---
        elif k == curses.KEY_UP and src.selected_idx > 0:
            src.selected_idx -= 1
            if src.selected_idx < src.top_idx: src.top_idx -= 1

        elif k == curses.KEY_DOWN and src.selected_idx < len(src.files) - 1:
            src.selected_idx += 1
            if src.selected_idx >= src.top_idx + (h-4): src.top_idx += 1

        # Page Up y Page Down
        elif k == curses.KEY_PPAGE:
            step = h - 4
            src.selected_idx = max(0, src.selected_idx - step)
            src.top_idx = max(0, src.top_idx - step)

        elif k == curses.KEY_NPAGE:
            step = h - 4
            src.selected_idx = min(len(src.files) - 1, src.selected_idx + step)
            if src.selected_idx >= src.top_idx + step:
                src.top_idx = min(len(src.files) - step, src.top_idx + step)
        # Tecla para crear disco nuevo (por ejemplo, 'n' de Nuevo)
        # --- Tecla para crear disco nuevo ('N') ---
        elif k in [ord('n'), ord('N')]:
            from operations import create_dsk_op
            
            # Determinamos la ruta de destino real del panel activo
            target_path = src.path if not src.is_dsk_mode else os.path.dirname(src.dsk_path)
            
            # Le pasamos la ruta destino a la operación
            res = create_dsk_op(stdscr, target_path) 
            
            if res:
                stdscr.attron(curses.A_REVERSE | curses.color_pair(1))
                stdscr.addstr(h-2, 0, f" {res} ".ljust(w-1))
                stdscr.attroff(curses.A_REVERSE | curses.color_pair(1))
                stdscr.getch()
            
            src.refresh() # Ahora sí refresca la carpeta correcta
        # Tecla F2 o 'r' para Renombrar
        elif k in [curses.KEY_F2, ord('r'), ord('R')]:
            from operations import rename_op
            err = rename_op(stdscr, src)
            if err:
                stdscr.addstr(h-2, 0, f" Error: {err[:w-10]} ".ljust(w-1), curses.A_REVERSE)
                stdscr.getch()
            src.refresh()
        # --- Comparar archivos con 'D' ---
        elif k in [ord('d'), ord('D')]:
            launch_diff(stdscr, p_izq, p_der, p_act)

        elif k in [curses.KEY_F10, ord('q'), ord('Q')]:
            break

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    finally:
        os.system("stty sane")
