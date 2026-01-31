import os
import subprocess
import curses
from config import FORMATO_DEFECTO, get_available_formats

class Panel:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.files = []
        self.is_dsk_mode = False
        self.selected_idx = 0
        self.top_idx = 0
        self.dsk_path = ""
        self.user_area = 0
        self.format = FORMATO_DEFECTO
        self.marked_indices = set() # Archivos seleccionados
        self.refresh()

    def refresh(self):
        if self.is_dsk_mode:
            self.files = self.get_cpm_files()
        else:
            try:
                items = os.listdir(self.path)
                dirs = sorted([d for d in items if os.path.isdir(os.path.join(self.path, d))])
                files = sorted([f for f in items if os.path.isfile(os.path.join(self.path, f))])
                
                # Guardamos (nombre, tamaño_formateado)
                self.files = [("..", "UP-DIR")]
                for d in dirs:
                    self.files.append((d, "SUB-DIR"))
                for f in files:
                    size = os.path.getsize(os.path.join(self.path, f))
                    self.files.append((f, self.format_size(size)))
            except: 
                self.files = [("..", "UP-DIR"), ("Error", "0")]
        
        if self.selected_idx >= len(self.files): self.selected_idx = 0

    def format_size(self, size):
        """Convierte bytes a formato legible (K, M)"""
        if size < 1024: return f"{size}B"
        elif size < 1024*1024: return f"{size//1024}K"
        else: return f"{size//(1024*1024)}M"

    def get_cpm_files(self):
        try:
            cmd = ["cpmls", "-l", "-f", self.format, self.dsk_path, f"{self.user_area}:*"]
            res = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
            
            # FUNCIONALIDAD PRESERVADA: Cabeceras de navegación originales
            files = [
                ("< VOLVER AL SISTEMA >", ""), 
                ("< CAMBIAR USER AREA >", ""), 
                ("< CAMBIAR FORMATO >", "")
            ]
            
            lines = res.strip().split('\n')
            for line in lines:
                parts = line.split()
                # Según tu debug, los archivos tienen 6 partes
                if len(parts) == 6:
                    name = parts[5].lower() # El nombre está en el índice 5
                    
                    # Convertimos los bytes del índice 1 a K para que se vea prolijo
                    try:
                        bytes_size = int(parts[1])
                        size_str = f"{max(1, bytes_size // 1024)}K"
                    except:
                        size_str = "0K"
                        
                    files.append((name, size_str))
            return files
        except Exception: 
            return [("< ERROR DE LECTURA >", "")]
    def get_marked_size(self):
        """Calcula el total de bytes de los archivos seleccionados"""
        total = 0
        for idx in self.marked_indices:
            item = self.files[idx]
            name = item[0] if isinstance(item, tuple) else item
            
            if self.is_dsk_mode:
                # En modo DSK, intentamos extraer el número del string "14K"
                size_str = item[1] if isinstance(item, tuple) else "0"
                try:
                    # Quitamos la 'K' y multiplicamos por 1024
                    k_size = int(size_str.replace('K', ''))
                    total += k_size * 1024
                except: pass
            else:
                # En modo local, usamos el tamaño real del archivo en disco
                try:
                    total += os.path.getsize(os.path.join(self.path, name))
                except: pass
        return total
    def toggle_mark(self):
        """Marca o desmarca archivos para selección múltiple"""
        if not self.files:
            return
        
        # Obtenemos el nombre del item actual (tupla o string "..")
        item = self.files[self.selected_idx]
        fn = item[0] if isinstance(item, tuple) else item

        # No permitimos marcar cabeceras de sistema o el directorio superior
        if not fn.startswith("<") and fn != "..":
            if self.selected_idx in self.marked_indices:
                self.marked_indices.remove(self.selected_idx)
            else:
                self.marked_indices.add(self.selected_idx)

            # Movimiento automático hacia abajo como en el Midnight Commander original
            if self.selected_idx < len(self.files) - 1:
                self.selected_idx += 1
        
        # El redibujado se hace desde el bucle principal de zmc.py, 
        # pero si querés forzarlo aquí, podés llamar a draw si lo definís abajo

    def draw(self, win, h, w, is_active):
        """Dibuja el panel con el look v4.8 (Separador vertical y colores)"""
        win.erase()
        win.box()
        
        # Título del panel (Ruta o Disco)
        title = f" {os.path.basename(self.dsk_path) if self.is_dsk_mode else self.path} "
        win.addstr(0, 2, title[:w-4], curses.A_BOLD)

        for i in range(h - 2):
            idx = i + self.top_idx
            if idx >= len(self.files): break
            
            item = self.files[idx]
            name = item[0] if isinstance(item, tuple) else item
            size = item[1] if isinstance(item, tuple) else ""

            # LÓGICA DE COLORES
            if is_active and idx == self.selected_idx:
                attr = curses.color_pair(3) | curses.A_BOLD # Barra de selección
            elif idx in self.marked_indices:
                attr = curses.color_pair(4) | curses.A_BOLD # ARCHIVO MARCADO (AMARILLO)
            else:
                attr = curses.color_pair(1) # Normal

            # Dibujamos nombre y tamaño con el separador vertical "│"
            name_w = w - 10
            line = f" {name[:name_w-1].ljust(name_w-1)}│{size:>6} "
            try:
                win.addstr(i + 1, 1, line[:w-2], attr)
            except: pass
            
        win.refresh()
    def get_marked_files(self):
        """Retorna solo los nombres para que F5, F6 y F8 no fallen"""
        if not self.marked_indices:
            raw = self.files[self.selected_idx]
            return [raw[0] if isinstance(raw, tuple) else raw]
        
        return [self.files[i][0] if isinstance(self.files[i], tuple) else self.files[i] 
                for i in self.marked_indices]

    def action(self, stdscr):
        # Definimos item_raw primero para evitar el error de variable no definida
        item_raw = self.files[self.selected_idx]
        # Extraemos solo el nombre para que el resto de la lógica no cambie
        item = item_raw[0] if isinstance(item_raw, tuple) else item_raw
        
        if self.is_dsk_mode:
            if item == "< VOLVER AL SISTEMA >":
                self.is_dsk_mode = False; self.marked_indices.clear(); self.refresh()
            elif item == "< CAMBIAR USER AREA >":
                h, w = stdscr.getmaxyx()
                stdscr.addstr(h-2, 0, " Área (0-15): ".ljust(w-1), curses.A_REVERSE)
                curses.echo(); u = stdscr.getstr(h-2, 15, 2).decode(); curses.noecho()
                if u.isdigit(): self.user_area = int(u)
                self.marked_indices.clear(); self.refresh()
            elif item == "< CAMBIAR FORMATO >":
                self.change_format(stdscr)
        else:
            new_p = os.path.join(self.path, item)
            if os.path.isdir(new_p):
                self.path, self.selected_idx, self.top_idx = os.path.abspath(new_p), 0, 0
                self.marked_indices.clear(); self.refresh()
            elif item.lower().endswith(".dsk"):
                self.dsk_path, self.is_dsk_mode, self.selected_idx, self.top_idx = new_p, True, 0, 0
                self.user_area = 0; self.marked_indices.clear(); self.refresh()

    def change_format(self, stdscr):
        formats = get_available_formats()
        sel = 0; offset = 0
        while True:
            h, w = stdscr.getmaxyx(); max_v = h - 6
            stdscr.clear(); stdscr.addstr(1, 2, " SELECCIONE FORMATO (ENTER): ", curses.A_BOLD)
            for i in range(max_v):
                idx = i + offset
                if idx < len(formats):
                    if idx == sel:
                        stdscr.attron(curses.A_REVERSE); stdscr.addstr(i+3, 4, f" > {formats[idx].ljust(w-10)} "); stdscr.attroff(curses.A_REVERSE)
                    else: stdscr.addstr(i+3, 4, f"   {formats[idx]} ")
            stdscr.refresh(); k = stdscr.getch()
            if k == curses.KEY_UP and sel > 0:
                sel -= 1
                if sel < offset: offset -= 1
            elif k == curses.KEY_DOWN and sel < len(formats)-1:
                sel += 1
                if sel >= offset + max_v: offset += 1
            elif k == 10: self.format = formats[sel]; break
            elif k == 27: break
        self.marked_indices.clear(); self.refresh()
def show_selection_menu(stdscr, items, title):
    """Muestra un menú simple de selección."""
    h, w = stdscr.getmaxyx()
    win_h, win_w = 15, 30
    win = curses.newwin(win_h, win_w, (h-win_h)//2, (w-win_w)//2)
    win.keypad(True)
    win.box()
    win.addstr(0, 2, f" {title} ")
    
    current_idx = 0
    while True:
        for i, item in enumerate(items[:win_h-2]): # Limitamos a la altura de la ventana
            style = curses.A_REVERSE if i == current_idx else curses.A_NORMAL
            win.addstr(i + 1, 2, item.ljust(win_w-4), style)
        
        key = win.getch()
        if key == curses.KEY_UP and current_idx > 0: current_idx -= 1
        elif key == curses.KEY_DOWN and current_idx < len(items) - 1: current_idx += 1
        elif key == ord('\n'): return items[current_idx] # Enter selecciona
        elif key == 27: return None # ESC cancela
        win.refresh()
