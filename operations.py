import os
import subprocess
import shutil
import time
import curses
from config import TMP_DIR, EDITOR, VISOR, FSED
import re

def rename_op(stdscr, src):
    """Cambia el nombre de un archivo. Si es CP/M, usa un puente temporal."""
    files = src.get_marked_files()
    if not files: return
    
    # Aseguramos que sea string
    old_raw = files[0]
    old_name = old_raw[0] if isinstance(old_raw, tuple) else old_raw

    h, w = stdscr.getmaxyx()
    stdscr.attron(curses.A_REVERSE)
    stdscr.addstr(h-2, 0, f" Nuevo nombre para {old_name}: ".ljust(w-1))
    stdscr.attroff(curses.A_REVERSE)
    
    curses.echo()
    new_name = stdscr.getstr(h-2, len(old_name) + 20, 20).decode().strip().upper()
    curses.noecho()
    
    if not new_name: return

    try:
        if src.is_dsk_mode:
            # MÉTODO COMPATIBLE: Extraer -> Borrar -> Inyectar
            bridge_p = os.path.join(TMP_DIR, f"rename_{old_name}")
            
            # 1. Extraemos con el nombre viejo
            subprocess.run(["cpmcp", "-f", src.format, src.dsk_path, f"{src.user_area}:{old_name}", bridge_p], check=True)
            # 2. Borramos el viejo
            subprocess.run(["cpmrm", "-f", src.format, src.dsk_path, f"{src.user_area}:{old_name}"], check=True)
            # 3. Inyectamos con el nombre nuevo
            subprocess.run(["cpmcp", "-f", src.format, src.dsk_path, bridge_p, f"{src.user_area}:{new_name}"], check=True)
            
            if os.path.exists(bridge_p): os.remove(bridge_p)
        else:
            # En Linux usamos el os.rename de siempre
            os.rename(os.path.join(src.path, old_name), os.path.join(src.path, new_name))
        return None 
    except Exception as e:
        return str(e)

def create_dsk_op(stdscr, dest_path): # <--- Ahora recibe la ruta destino
    formats = get_available_formats()
    chosen_format = show_selection_menu(stdscr, formats, "Select Format for New Disk")

    if not chosen_format:
        return None

    h, w = stdscr.getmaxyx()
    stdscr.attron(curses.A_REVERSE)
    stdscr.addstr(h-2, 0, " Nombre del nuevo disco: ".ljust(w-1))
    stdscr.attroff(curses.A_REVERSE)

    curses.echo()
    dsk_name = stdscr.getstr(h-2, 25, 20).decode().strip()
    curses.noecho()

    if dsk_name:
        if not dsk_name.lower().endswith(".dsk"):
            dsk_name += ".dsk"

        # CONSTRUIMOS LA RUTA ABSOLUTA
        full_dsk_path = os.path.join(dest_path, dsk_name)

        try:
            fmt_lower = chosen_format.lower()
            size_kb = 512 

            if "8meg" in fmt_lower: size_kb = 8192
            elif any(x in fmt_lower for x in ["hd", "hard", "z80pack"]): size_kb = 4096
            elif any(x in fmt_lower for x in ["osborne", "apple", "cpm80"]): size_kb = 256

            # 1. Creamos el contenedor en la ruta correcta
            subprocess.run(["truncate", "-s", f"{size_kb}K", full_dsk_path], check=True)

            # 2. Aplicamos formato mkfs.cpm
            subprocess.run(["mkfs.cpm", "-f", chosen_format, full_dsk_path], check=True, capture_output=True)

            # 3. Inyectamos README (Funcionalidad preservada)
            label_fn = "README.TXT"
            label_path = os.path.join(TMP_DIR, label_fn)
            with open(label_path, "w") as f:
                f.write(f"ZMC v4.8 - lu1pvt\nDISK: {dsk_name}\nFORMAT: {chosen_format}\n")

            # Inyectamos usando la ruta absoluta del nuevo disco
            subprocess.run(["cpmcp", "-f", chosen_format, full_dsk_path, label_path, f"0:{label_fn}"], check=True)

            if os.path.exists(label_path): os.remove(label_path)

            return f"ÉXITO: {dsk_name} creado en el panel actual."

        except Exception as e:
            return f"Error: {str(e)}"

    return None

def show_selection_menu(stdscr, items, title):
    h, w = stdscr.getmaxyx()
    win_h, win_w = 20, 45  # Un poco más grande para que quepan bien los nombres
    win = curses.newwin(win_h, win_w, (h-win_h)//2, (w-win_w)//2)
    win.keypad(True)  # CLAVE: Permite capturar KEY_UP y KEY_DOWN
    win.box()
    win.addstr(0, 2, f" {title} ", curses.A_BOLD)
    
    current_idx = 0
    offset = 0  # Para manejar el scroll si la lista es muy larga

    while True:
        # Dibujamos solo los ítems que caben en la ventana
        for i in range(win_h - 2):
            idx = i + offset
            if idx < len(items):
                style = curses.A_REVERSE if idx == current_idx else curses.A_NORMAL
                win.addstr(i + 1, 2, items[idx].ljust(win_w-4), style)
            else:
                win.addstr(i + 1, 2, " " * (win_w-4)) # Limpia líneas sobrantes
        
        win.refresh()
        key = win.getch()
        
        if key == curses.KEY_UP:
            if current_idx > 0:
                current_idx -= 1
                if current_idx < offset:
                    offset -= 1 # Scroll hacia arriba
        elif key == curses.KEY_DOWN:
            if current_idx < len(items) - 1:
                current_idx += 1
                if current_idx >= offset + (win_h - 2):
                    offset += 1 # Scroll hacia abajo
        elif key == ord('\n'): # Enter selecciona
            return items[current_idx]
        elif key in [27, ord('q'), ord('Q')]: # ESC o Q cancela
            return None

def get_available_formats():
    """Lee las definiciones de diskdefs del sistema."""
    formats = []
    # Ruta estándar en Linux para cpmtools
    path = "/etc/cpmtools/diskdefs" 
    
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                for line in f:
                    # Buscamos líneas que empiecen con 'diskdef'
                    match = re.match(r'^diskdef\s+(\S+)', line)
                    if match:
                        formats.append(match.group(1))
        except Exception:
            pass
            
    # Si el archivo no existe o falla, devolvemos básicos
    if not formats:
        return ["z80pack-hdb", "ibm-3740", "apple-do", "osborne1"]
        
    return sorted(list(set(formats))) # Ordenados y sin duplicados

def launch_fsed(stdscr, p):
    """Lanza fsed.cpm directamente sobre el archivo .dsk"""
    if not p.is_dsk_mode: return
    
    curses.def_shell_mode()
    curses.endwin()
    os.system("stty sane")
    # fsed.cpm opera sobre el disco completo, no sobre un archivo interno
    os.system(f"{FSED} {p.dsk_path}")
    os.system("stty sane")
    stdscr.clear()
    stdscr.refresh()
    p.refresh()

def format_disk_op(stdscr, p):
    """Formatea un disco de cero usando mkfs.cpm"""
    if not p.is_dsk_mode: return
    
    h, w = stdscr.getmaxyx()
    msg = f" ¿ESTÁS SEGURO? Se borrará TODO en {p.format} (S/N): "
    stdscr.addstr(h-2, 0, msg.ljust(w-1), curses.A_REVERSE | curses.A_BOLD)
    
    if stdscr.getch() in [ord('s'), ord('S')]:
        try:
            # Comando mkfs.cpm: crea el sistema de archivos CP/M
            subprocess.run(["mkfs.cpm", "-f", p.format, p.dsk_path], check=True)
            stdscr.addstr(h-2, 0, " Disco formateado con éxito. ".ljust(w-1), curses.A_REVERSE)
            time.sleep(1)
        except Exception as e:
            stdscr.addstr(h-2, 0, f" Error: {str(e)} ".ljust(w-1), curses.A_REVERSE)
            time.sleep(2)
    
    stdscr.addstr(h-2, 0, " ".ljust(w-1))
    p.refresh()

def launch_tool(stdscr, p, tool):
    """Extrae el archivo del disco y lanza mcedit o mcview"""
    # 1. Obtenemos el elemento crudo de la lista (puede ser tupla o string)
    item_raw = p.files[p.selected_idx]
    
    # 2. Ahora sí usamos item_raw para extraer el nombre
    fn = item_raw[0] if isinstance(item_raw, tuple) else item_raw
    
    if fn.startswith("<") or fn == "..": return

    # --- FUNCIONALIDAD PRESERVADA: Puente temporal y extracción ---
    local_file = os.path.join(TMP_DIR, fn)

    if os.path.exists(local_file): os.remove(local_file)

    try:
        if p.is_dsk_mode:
            subprocess.run(["cpmcp", "-f", p.format, p.dsk_path, f"{p.user_area}:{fn}", local_file], check=True)
            # Sincronización (Preservada)
            for _ in range(20):
                if os.path.exists(local_file) and os.path.getsize(local_file) >= 0: break
                time.sleep(0.05)
        else:
            local_file = os.path.join(p.path, fn)

        # Lanzamiento de herramienta (mcview/mcedit)
        curses.def_shell_mode()
        curses.endwin()
        os.system("stty sane")
        os.system(f"{tool} {local_file}")
        os.system("stty sane")
        stdscr.clear()
        stdscr.refresh()

        # 3. RE-INYECCIÓN: Si editamos dentro de un DSK, guardamos cambios
        if p.is_dsk_mode and tool == EDITOR:
            time.sleep(0.1) # Pausa para que el editor suelte el archivo
            # Borramos la versión vieja e inyectamos la nueva en mayúsculas
            subprocess.run(["cpmrm", "-f", p.format, p.dsk_path, f"{p.user_area}:{fn}"], stderr=subprocess.DEVNULL)
            subprocess.run(["cpmcp", "-f", p.format, p.dsk_path, local_file, f"{p.user_area}:{fn.upper()}"], check=True)
            p.refresh()
            
    except Exception as e:
        pass 
    finally:
        # Limpieza del puente si era un archivo extraído de un DSK
        if p.is_dsk_mode and os.path.exists(local_file): os.remove(local_file)

def delete_op(src):
    """Borrado masivo o individual"""
    files = src.get_marked_files()
    for fn in files:
        if fn.startswith("<") or fn == "..": continue
        try:
            if src.is_dsk_mode:
                subprocess.run(["cpmrm", "-f", src.format, src.dsk_path, f"{src.user_area}:{fn}"], check=True)
            else:
                p_f = os.path.join(src.path, fn)
                if os.path.isdir(p_f): shutil.rmtree(p_f)
                else: os.remove(p_f)
        except: pass
    src.marked_indices.clear()
    src.refresh()

def file_op(src, dst, op_type, stdscr=None):
    files = src.get_marked_files()
    error_msg = None

    for f_raw in files:
        # Aseguramos que fn sea solo el nombre del archivo
        fn = f_raw[0] if isinstance(f_raw, tuple) else f_raw
        if fn.startswith("<") or fn == "..": continue
        # ... (Toda tu lógica de sobreescritura y cpmcp se mantiene intacta)
        bridge_p = os.path.join(TMP_DIR, f"bridge_{fn}")
        
        # --- NUEVA FUNCIONALIDAD: Confirmación de Sobreescritura ---
        if dst.is_dsk_mode and stdscr:
            # Verificamos si el archivo ya existe en el disco de destino
            # cpmls devuelve error si no encuentra el archivo
            check_cmd = ["cpmls", "-f", dst.format, dst.dsk_path, f"{dst.user_area}:{fn}"]
            exists = False
            try:
                subprocess.run(check_cmd, check=True, capture_output=True)
                exists = True
            except subprocess.CalledProcessError:
                exists = False

            if exists:
                h, w = stdscr.getmaxyx()
                # Mostramos la advertencia en la barra inferior
                stdscr.attron(curses.A_REVERSE | curses.color_pair(1))
                stdscr.addstr(h-2, 0, f" OVERWRITE {fn}? (S/N): ".ljust(w-1))
                stdscr.attroff(curses.A_REVERSE | curses.color_pair(1))
                stdscr.refresh()
                
                char = stdscr.getch()
                stdscr.addstr(h-2, 0, " ".ljust(w-1)) # Limpiamos el mensaje
                if char not in [ord('s'), ord('S'), ord('y'), ord('Y')]:
                    continue # Saltamos este archivo y seguimos con el siguiente
        # -----------------------------------------------------------

        try:
            # Extracción del origen (Funcionalidad preservada)
            if src.is_dsk_mode:
                subprocess.run(["cpmcp", "-f", src.format, src.dsk_path, f"{src.user_area}:{fn}", bridge_p],
                               check=True, capture_output=True)
            else:
                shutil.copy2(os.path.join(src.path, fn), bridge_p)

            # Sincronización breve (Funcionalidad preservada)
            for _ in range(10):
                if os.path.exists(bridge_p): break
                time.sleep(0.05)

            # Inyección al destino (Funcionalidad preservada)
            if dst.is_dsk_mode:
                # Quitamos el cpmrm automático anterior porque ahora preguntamos arriba
                subprocess.run(["cpmrm", "-f", dst.format, dst.dsk_path, f"{dst.user_area}:{fn}"], stderr=subprocess.DEVNULL)
                subprocess.run(["cpmcp", "-f", dst.format, dst.dsk_path, bridge_p, f"{dst.user_area}:{fn.upper()}"],
                               check=True, capture_output=True)
            else:
                # Si el destino es Linux, shutil.copy2 sobreescribe por defecto
                shutil.copy2(bridge_p, os.path.join(dst.path, fn))

            # Lógica de MOVE (Funcionalidad preservada)
            if op_type == "MOVE":
                if src.is_dsk_mode:
                    subprocess.run(["cpmrm", "-f", src.format, src.dsk_path, f"{src.user_area}:{fn}"], check=True)
                else:
                    os.remove(os.path.join(src.path, fn))

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip()
            break 
        except Exception as e:
            error_msg = str(e)
            break
        finally:
            if os.path.exists(bridge_p): os.remove(bridge_p)

    src.marked_indices.clear()
    src.refresh(); dst.refresh()
    return error_msg
