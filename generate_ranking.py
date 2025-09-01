from collections import defaultdict, Counter
from pathlib import Path
import argparse

DEFAULT_INPUT = "logs_clean.txt"

def cargar_eventos(ruta: Path):
    """Lee líneas en formato: 'FECHA | Killer -> Target'"""
    kills = defaultdict(int)
    deaths = defaultdict(int)
    kills_by = defaultdict(Counter)   # killer -> Counter(target)
    deaths_by = defaultdict(Counter)  # target -> Counter(killer)

    if not ruta.exists():
        raise SystemExit(f"No existe el archivo de entrada: {ruta}")

    with ruta.open("r", encoding="utf-8", errors="ignore") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or "|" not in linea or "->" not in linea:
                continue
            try:
                _, accion = linea.split("|", 1)
                killer, target = accion.split("->", 1)
            except ValueError:
                continue
            killer = killer.strip()
            target = target.strip()
            if not killer or not target:
                continue
            kills[killer] += 1
            deaths[target] += 1
            kills_by[killer][target] += 1
            deaths_by[target][killer] += 1

    return kills, deaths, kills_by, deaths_by

def generar_ranking(kills, deaths):
    jugadores = set(kills) | set(deaths)
    ranking = []
    for j in jugadores:
        k = kills[j]
        d = deaths[j]
        ranking.append((j, k, d, k - d))
    ranking.sort(key=lambda x: (x[3], x[1], -x[2], x[0].lower()), reverse=True)
    return ranking

def imprimir_ranking(ranking, top=None):
    print(f"{'#':<4} {'Jugador':<20} {'Kills':<7} {'Deaths':<7} {'K-D':<5}")
    print("-" * 50)
    data = ranking if top is None else ranking[:top]
    for i, (j, k, d, diff) in enumerate(data, 1):
        print(f"{i:<4} {j:<20} {k:<7} {d:<7} {diff:<5}")

def breakdown_jugador(nombre: str, kills, deaths, kills_by, deaths_by, top=10):
    k = kills[nombre]
    d = deaths[nombre]
    print(f"Jugador: {nombre}")
    print(f"Kills: {k} | Deaths: {d} | K-D: {k - d}")
    print("\nVictimas más frecuentes:")
    if nombre in kills_by and kills_by[nombre]:
        for victima, cnt in kills_by[nombre].most_common(top):
            print(f"  {victima}: {cnt}")
    else:
        print("  (sin datos)")
    print("\nAsesinos más frecuentes (quién lo mató):")
    if nombre in deaths_by and deaths_by[nombre]:
        for asesino, cnt in deaths_by[nombre].most_common(top):
            print(f"  {asesino}: {cnt}")
    else:
        print("  (sin datos)")

def menu_interactivo(ruta: Path):
    kills, deaths, kills_by, deaths_by = cargar_eventos(ruta)
    ranking = generar_ranking(kills, deaths)

    while True:
        print("\n=== MENU RANKING ===")
        print("1) Ver ranking global")
        print("2) Ver ranking individual por jugador")
        print("3) Exportar ranking global a archivo")
        print("4) Salir")
        op = input("> Selecciona una opción: ").strip()
        if op == "1":
            try:
                top_str = input("  ¿Top N? (Enter para todos): ").strip()
                top = int(top_str) if top_str else None
            except ValueError:
                top = None
            imprimir_ranking(ranking, top=top)
        elif op == "2":
            nombre = input("  Ingresa el nombre exacto del jugador: ").strip()
            if not nombre:
                continue
            if nombre not in (set(kills) | set(deaths)):
                print("  Jugador no encontrado en los datos.")
                continue
            breakdown_jugador(nombre, kills, deaths, kills_by, deaths_by)
        elif op == "3":
            ruta_out = input("  Nombre del archivo de salida (default ranking_final.txt): ").strip() or "ranking_final.txt"
            out = Path(ruta_out)
            with out.open("w", encoding="utf-8") as f:
                f.write(f"{'#':<4} {'Jugador':<20} {'Kills':<7} {'Deaths':<7} {'K-D':<5}\n")
                f.write("-" * 50 + "\n")
                for i, (j, k, d, diff) in enumerate(ranking, 1):
                    f.write(f"{i:<4} {j:<20} {k:<7} {d:<7} {diff:<5}\n")
            print(f"  Archivo guardado en {out}")
        elif op == "4":
            break
        else:
            print("  Opción inválida.")

def main():
    parser = argparse.ArgumentParser(description="Genera ranking global o individual desde logs limpios")
    parser.add_argument("--input", "-i", type=str, default=DEFAULT_INPUT, help=f"Archivo de entrada (default: {DEFAULT_INPUT})")
    args = parser.parse_args()
    ruta = Path(args.input)
    menu_interactivo(ruta)

if __name__ == "__main__":
    main()
