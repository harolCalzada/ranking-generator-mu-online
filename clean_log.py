import re
import argparse
from pathlib import Path

DATE_PATTERN = re.compile(r"([A-Za-z]+\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}\s+[AP]M)")
KILL_PATTERN = re.compile(r"\[\s*([^\]]+)\s*\]\s*killed\s*\[\s*([^\]]+)\s*\]", re.IGNORECASE)

def _strip_markdown_artifacts(s: str) -> str:
    """Remove common markdown/code artifacts and extra punctuation surrounding entries."""
    # Remove bold/italics/backticks and stray exclamation marks around tokens
    return (
        s.replace("**", "")
         .replace("*", "")
         .replace("`", "")
         .replace("!`", "!")
    )

def limpiar_logs_texto(texto: str) -> list[str]:
    """
    Limpia logs con formatos desordenados donde puede haber:
    - Fechas repetidas en la misma línea (e.g. "*Aug 31...*Aug 31...*")
    - Artefactos de Markdown (**, *, `) y signos extras
    - Eventos en formato "[Killer] killed [Target]"

    Devuelve una lista de líneas: "<FECHA> | <Killer> -> <Target>".
    """
    resultados: list[str] = []
    fecha_actual: str | None = None
    pendientes: list[tuple[str, str]] = []  # lista de (killer, target) a la espera de fecha

    for raw_line in texto.splitlines():
        linea = _strip_markdown_artifacts(raw_line).strip()
        if not linea:
            continue

        # Buscar evento de kill primero
        kill_match = KILL_PATTERN.search(linea)
        if kill_match:
            killer = kill_match.group(1).strip()
            target = kill_match.group(2).strip()
            if fecha_actual:
                resultados.append(f"{fecha_actual} | {killer} -> {target}")
            else:
                # Guardamos en cola hasta que llegue la próxima fecha
                pendientes.append((killer, target))

        # Capturar la última fecha presente en la línea, si existe
        fechas = DATE_PATTERN.findall(linea)
        if fechas:
            # Si hay fechas repetidas en la línea, nos quedamos con la última (más a la derecha)
            fecha_actual = fechas[-1]
            # Si había kills pendientes sin fecha previa, los asociamos a esta fecha
            if pendientes:
                for k, t in pendientes:
                    resultados.append(f"{fecha_actual} | {k} -> {t}")
                pendientes = []

    return resultados

def limpiar_archivo(entrada: Path, salida: Path) -> int:
    contenido = entrada.read_text(encoding="utf-8", errors="ignore")
    limpio = limpiar_logs_texto(contenido)
    salida.write_text("\n".join(limpio) + ("\n" if limpio else ""), encoding="utf-8")
    return len(limpio)

def main():
    parser = argparse.ArgumentParser(description="Limpia logs y genera logs_clean.txt")
    parser.add_argument("input", type=str, help="Ruta del archivo de logs crudos")
    parser.add_argument("--output", "-o", type=str, default="logs_clean.txt", help="Ruta del archivo de salida (por defecto logs_clean.txt)")
    args = parser.parse_args()

    entrada = Path(args.input)
    salida = Path(args.output)
    if not entrada.exists():
        raise SystemExit(f"No existe el archivo de entrada: {entrada}")

    n = limpiar_archivo(entrada, salida)
    print(f" Limpieza completa. {n} eventos guardados en: {salida}")

if __name__ == "__main__":
    main()
