import os
import re
import tempfile

# Variables de configuración (Preservadas)
FORMATO_DEFECTO = "z80pack-hd"
EDITOR = "mcedit"
VISOR = "mcview"
FSED = "fsed.cpm"

# MEJORA: Usamos el manejador de temporales del sistema para evitar conflictos de permisos
TMP_DIR = os.path.join(tempfile.gettempdir(), "zmc_work")

DISKDEFS_PATH = "/etc/cpmtools/diskdefs"

# Aseguramos la existencia con permisos amplios para el taller
try:
    if not os.path.exists(TMP_DIR):
        os.makedirs(TMP_DIR, mode=0o777, exist_ok=True)
    else:
        # Si ya existe, nos aseguramos de que sea escribible
        os.chmod(TMP_DIR, 0o777)
except Exception:
    # Si falla por permisos de sistema, caemos en una ruta local segura
    TMP_DIR = os.path.expanduser("~/.zmc_work")
    os.makedirs(TMP_DIR, exist_ok=True)

def get_available_formats():
    """Escanea diskdefs para el menú de F9 y formateo (Funcionalidad Preservada)"""
    formats = ["ibm-3740", "z80pack-hd", "z80pack-hdb"]
    if os.path.exists(DISKDEFS_PATH):
        try:
            with open(DISKDEFS_PATH, "r") as f:
                content = f.read()
                found = re.findall(r"diskdef\s+([^\s\n]+)", content)
                formats.extend(found)
        except: pass
    return sorted(list(set(formats)))
