# Ranking de Kills – Proyecto

Dashboard y utilidades para limpiar logs de kills, generar rankings y visualizar métricas (ELO, rachas, logros) en Streamlit.

## Estructura
- `clean_log.py`: limpia logs crudos y produce `logs_clean.txt`.
- `generate_ranking.py`: CLI para ver ranking global/individual en terminal.
- `stats.py`: módulo con parsing, agregados, ELO, rachas, rivales, etc.
- `app.py`: dashboard Streamlit (Ranking, ELO, Jugador, Logros, Tiempo).
- `requirements.txt`: dependencias.

## Requisitos
- Python 3.9+
- macOS/Linux/Windows

## Instalación rápida
```bash
# 1) Clona o copia este repo
# 2) (Opcional) Crea un entorno virtual
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3) Instala dependencias
pip install -r requirements.txt
```

## 1) Limpiar logs crudos
Entrada: un txt con eventos no estructurados. Salida: líneas `FECHA | Killer -> Target`.
```bash
python3 clean_log.py "./logs rdm 31 -08 -2025.txt" -o logs_clean.txt
# Ejemplo de salida final:
# August 31, 2025 6:04 PM | DeadPoll -> R3APER
```

Notas de limpieza:
- No se deduplican eventos (se cuentan todos).
- Soporta múltiples kills antes de detectar fecha; se asignan a la siguiente fecha encontrada.

### Formato de entrada esperado (para `app.py` y `stats.py`)
El dashboard y el módulo `stats.py` esperan un archivo de texto (por defecto `logs_clean.txt`) con **una línea por evento** en el formato:

```
<FECHA> | <Killer> -> <Target>
```

Donde:
- **FECHA** debe seguir el patrón en inglés: `Month DD, YYYY hh:mm AM/PM`
  - Ej.: `August 31, 2025 6:04 PM`
  - Regex usada en el parser (`stats.py`): `([A-Za-z]+\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}\s+[AP]M)`
- **Killer** y **Target** son nombres tal como aparecen en los logs.

Ejemplos válidos:
```
August 31, 2025 6:04 PM | DeadPoll -> R3APER
August 31, 2025 6:05 PM | XxKr0n0sxX -> CHIFLADO
```

Notas:
- El limpiador `clean_log.py` genera precisamente este formato a partir de logs crudos desordenados.
- No se asume zona horaria; las fechas se tratan como *naive* y solo se usan para ordenar cronológicamente.
- Si tus fuentes están en español, asegúrate de pasar primero por `clean_log.py` para normalizar a este formato.

## 2) CLI de ranking en terminal
```bash
python3 -m generate_ranking
```
Funciones:
- Ranking global (Top N configurable)
- Ranking individual por jugador (víctimas y asesinos más frecuentes)
- Exportar ranking global a archivo

## 3) Dashboard Streamlit
```bash
streamlit run app.py
```
Abrirá en:
- Local URL: http://localhost:8501
- Network URL: http://<tu-ip-local>:8501 (amigos en tu misma red)

Pestañas:
- Ranking: tabla y barras por K-D.
- ELO: ranking por ELO (cada kill es una “victoria” del killer sobre el target; K=32, inicial 1000).
- Jugador: métricas individuales, rachas y rivales frecuentes.
- Logros: tablas Top 10 por kills, K-D (umbral de actividad), eficiencia, rachas, ELO, víctimas/asesinos únicos. Incluye leyenda explicativa.
- Tiempo: actividad por minuto.

Si ves errores de caché en Streamlit:
```bash
streamlit cache clear
# y luego
streamlit run app.py
```

## Compartir el dashboard
### Opción A: misma red (rápida)
Comparte la Network URL mientras `streamlit run app.py` esté activo.

### Opción B: ngrok (URL pública temporal)
1. Instala ngrok (con Homebrew en macOS):
```bash
brew install --cask ngrok
```
2. Crea cuenta y copia tu Authtoken: https://dashboard.ngrok.com
3. Configura el token:
```bash
ngrok config add-authtoken TU_AUTHTOKEN
```
4. Arranca el dashboard local:
```bash
streamlit run app.py
```
5. Abre el túnel:
```bash
ngrok http 8501
```
6. Comparte la URL `https://xxxx.ngrok.io`.

Tips:
- Mantén abiertas las terminales de Streamlit y ngrok.
- Free tier puede caducar; vuelve a ejecutar el comando si se corta.

### Opción C: Streamlit Community Cloud (gratis, público)
1. Sube el repo a GitHub (incluye `app.py`, `stats.py`, `requirements.txt`).
2. Opcional: incluye `logs_clean.txt` de ejemplo o agrega un `file_uploader` en `app.py`.
3. Ve a https://share.streamlit.io → “New app” → selecciona repo/branch y `app.py`.
4. Obtén una URL pública.

## Comandos útiles
```bash
# Entorno
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Limpieza de logs
python3 clean_log.py "./logs rdm 31 -08 -2025.txt" -o logs_clean.txt

# CLI de ranking
python3 -m generate_ranking

# Dashboard
streamlit run app.py
streamlit cache clear

# ngrok
ngrok config add-authtoken TU_AUTHTOKEN
ngrok http 8501

# Git básico
git init
git add .
git commit -m "init"
```

## Cómo funciona ELO (resumen)
- Cada kill se considera una victoria del killer sobre el target.
- Fórmula: `R' = R + K * (score - expected)`, con `K=32`, `expected = 1/(1 + 10^((Rrival-Rpropio)/400))`.
- Se procesa cronológicamente según la marca de tiempo.

## Notas finales
- El sistema no elimina duplicados por diseño.
- Puedes ajustar parámetros (K del ELO, mínimos de eventos) editando `stats.py` y la sidebar en `app.py`.
