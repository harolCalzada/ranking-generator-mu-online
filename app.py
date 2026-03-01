from __future__ import annotations
import streamlit as st
import pandas as pd
import altair as alt
from pathlib import Path
from stats import load_events, aggregate, ranking, compute_top_rivals, compute_head_to_head, compute_streaks, compute_elo

DEFAULT_INPUT = "logs_clean.txt"

@st.cache_data(show_spinner=False)
def load_all(path: Path):
    events = load_events(path)
    kills, deaths, kills_by, deaths_by = aggregate(events)
    rank = ranking(kills, deaths)
    max_kill, max_death = compute_streaks(events)
    elo_map, elo_rank = compute_elo(events)
    return events, kills, deaths, kills_by, deaths_by, rank, max_kill, max_death, elo_map, elo_rank


def ranking_df(rank):
    return pd.DataFrame(rank, columns=["Jugador", "Kills", "Deaths", "K-D"])\
             .assign(Ranking=lambda df: range(1, len(df)+1))[["Ranking","Jugador","Kills","Deaths","K-D"]]


def elo_df(elo_rank):
    return pd.DataFrame([(p, round(r,1)) for p, r in elo_rank], columns=["Jugador","ELO"])\
             .assign(Ranking=lambda df: range(1, len(df)+1))[["Ranking","Jugador","ELO"]]


def events_df(events):
    return pd.DataFrame([{
        "ts": e.ts if e.ts is not None else pd.NaT,
        "killer": e.killer,
        "target": e.target
    } for e in events])


def main():
    st.set_page_config(page_title="Ranking Dashboard", layout="wide")
    st.title("Ranking Dashboard")

    # Sidebar controls
    st.sidebar.header("Filtros")
    input_path = st.sidebar.text_input("Archivo de entrada", value=DEFAULT_INPUT)
    path = Path(input_path)
    if not path.exists():
        st.error(f"No existe el archivo: {path}")
        st.stop()

    events, kills, deaths, kills_by, deaths_by, rank, max_kill, max_death, elo_map, elo_rank = load_all(path)
    df_rank = ranking_df(rank)
    df_elo = elo_df(elo_rank)
    df_events = events_df(events)

    # Filters (moved to sidebar)
    players = sorted(set(list(kills.keys()) + list(deaths.keys())))
    top_n = st.sidebar.number_input(
        "Top N (ranking)", min_value=1, max_value=max(1, len(df_rank)), value=min(20, len(df_rank))
    )
    # Quick search for player
    q = st.sidebar.text_input("Buscar jugador", value="")
    filtered_players = [p for p in players if q.lower() in p.lower()] if q else players
    player = st.sidebar.selectbox("Jugador (vista individual)", options=["(ninguno)"] + filtered_players)
    show_raw = st.sidebar.checkbox("Mostrar eventos crudos", value=False)

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Ranking", "ELO", "Jugador", "Logros", "Tiempo"])

    with tab1:
        st.subheader("Ranking Global (K-D)")
        st.dataframe(df_rank.head(int(top_n)), use_container_width=True)
        # simple bar chart of K-D
        chart = alt.Chart(df_rank.head(int(top_n))).mark_bar().encode(
            x=alt.X('K-D:Q'),
            y=alt.Y('Jugador:N', sort='-x')
        )
        st.altair_chart(chart, use_container_width=True)

    with tab2:
        st.subheader("Ranking ELO")
        st.dataframe(df_elo.head(int(top_n)), use_container_width=True)
        chart_elo = alt.Chart(df_elo.head(int(top_n))).mark_bar().encode(
            x=alt.X('ELO:Q'),
            y=alt.Y('Jugador:N', sort='-x')
        )
        st.altair_chart(chart_elo, use_container_width=True)

    with tab3:
        st.subheader("Vista por Jugador")
        if player and player != "(ninguno)":
            k = kills[player]
            d = deaths[player]
            st.metric("Kills", k)
            st.metric("Deaths", d)
            st.metric("K-D", k - d)
            st.metric("Kill Streak máx", max_kill.get(player, 0))
            st.metric("Death Streak máx", max_death.get(player, 0))

            victims, killers = compute_top_rivals(player, kills_by, deaths_by, top=15)
            col_v, col_k = st.columns(2)
            with col_v:
                st.write("Victimas más frecuentes")
                st.table(pd.DataFrame(victims, columns=["Victima", "Veces"]))
            with col_k:
                st.write("Asesinos más frecuentes")
                st.table(pd.DataFrame(killers, columns=["Asesino", "Veces"]))
        else:
            st.info("Selecciona un jugador en el panel lateral.")

    with tab4:
        st.subheader("Logros (Leaderboards)")
        # Umbral para rankings que requieren actividad suficiente
        min_events = st.sidebar.number_input(
            "Mín. eventos (KD/Eficiencia)", min_value=1, max_value=1000, value=10,
            help="Número mínimo de participaciones (kills + deaths) para que un jugador entre en los rankings de K-D y Eficiencia. Evita outliers con pocas jugadas."
        )

        with st.expander("¿Qué significa cada logro?", expanded=False):
            st.markdown(
                """
                - **Más kills**: jugadores con mayor cantidad total de kills.
                - **Mejor K-D**: diferencia `Kills - Deaths`. Se aplica el umbral de *Mín. eventos* para evitar sesgos por poca actividad.
                - **Mayor Eficiencia**: `Kills / (Kills + Deaths)` con umbral de *Mín. eventos*.
                - **Mayor racha de kills**: secuencia más larga de kills consecutivos sin morir (kill streak máximo).
                - **Mayor racha de muertes**: secuencia más larga de muertes consecutivas sin conseguir un kill.
                - **Mayor ELO**: rating dinámico ponderado por la fuerza del rival; cada kill cuenta como victoria frente al objetivo.
                - **Más víctimas únicas**: cantidad de rivales distintos a los que mató al menos una vez.
                - **Más asesinos únicos**: cantidad de rivales distintos que lo mataron al menos una vez.
                """
            )

        # Base de conteos
        df_counts = pd.DataFrame(
            [(p, kills.get(p, 0), deaths.get(p, 0)) for p in players],
            columns=["Jugador", "Kills", "Deaths"]
        )
        df_counts["Eventos"] = df_counts["Kills"] + df_counts["Deaths"]
        df_counts["K-D"] = df_counts["Kills"] - df_counts["Deaths"]
        df_counts["Eficiencia"] = (df_counts["Kills"] / df_counts["Eventos"]).fillna(0.0)

        # Streaks
        streak_df = pd.DataFrame(
            sorted(max_kill.items(), key=lambda x: x[1], reverse=True),
            columns=["Jugador", "MaxKillStreak"]
        )
        death_streak_df = pd.DataFrame(
            sorted(max_death.items(), key=lambda x: x[1], reverse=True),
            columns=["Jugador", "MaxDeathStreak"]
        )

        # Únicas víctimas / asesinos
        victims_unique_df = pd.DataFrame(
            [(p, len(kills_by.get(p, {}))) for p in players],
            columns=["Jugador", "VictimasUnicas"]
        ).sort_values("VictimasUnicas", ascending=False)
        killers_unique_df = pd.DataFrame(
            [(p, len(deaths_by.get(p, {}))) for p in players],
            columns=["Jugador", "AsesinosUnicos"]
        ).sort_values("AsesinosUnicos", ascending=False)

        # Eficiencia y Actividad
        eff_df = (
            df_counts[df_counts["Eventos"] >= int(min_events)]
            .sort_values(["Eficiencia", "Kills"], ascending=[False, False])
        )
        active_df = df_counts.sort_values("Eventos", ascending=False)

        col1, col2 = st.columns(2)
        with col1:
            st.write("Más kills (Top 10)")
            st.caption("Total de kills acumuladas por jugador.")
            st.table(df_counts.sort_values("Kills", ascending=False).head(10)[["Jugador", "Kills"]])

            st.write("Mejor K-D (Top 10)")
            st.caption("Ordenado por K-D = Kills - Deaths. Requiere cumplir el mínimo de eventos.")
            st.table(
                df_counts[df_counts["Eventos"] >= int(min_events)]
                .sort_values(["K-D", "Kills"], ascending=[False, False])
                .head(10)[["Jugador", "K-D", "Kills", "Deaths", "Eventos"]]
            )

            st.write("Mayor Eficiencia (Top 10)")
            st.caption("Eficiencia = Kills / (Kills + Deaths). Requiere cumplir el mínimo de eventos.")
            st.table(
                eff_df.head(10)[["Jugador", "Eficiencia", "Kills", "Deaths", "Eventos"]]
            )

        with col2:
            st.write("Mayor racha de kills (Top 10)")
            st.caption("Kill streak más largo (kills consecutivos sin morir).")
            st.table(streak_df.head(10))

            st.write("Mayor racha de muertes (Top 10)")
            st.caption("Muertes consecutivas más largas sin conseguir un kill.")
            st.table(death_streak_df.head(10))

            st.write("Mayor ELO (Top 10)")
            st.caption("Rating Elo calculado cronológicamente; ganar a rivales fuertes suma más.")
            st.table(df_elo.head(10))

        col3, col4 = st.columns(2)
        with col3:
            st.write("Más víctimas únicas (Top 10)")
            st.caption("Número de rivales distintos a los que mató al menos una vez.")
            st.table(victims_unique_df.head(10))
        with col4:
            st.write("Más asesinos únicos (Top 10)")
            st.caption("Número de rivales distintos que lo mataron al menos una vez.")
            st.table(killers_unique_df.head(10))

    with tab5:
        st.subheader("Actividad en el tiempo")
        if not df_events.empty and df_events['ts'].notna().any():
            ts_df = df_events.dropna(subset=['ts']).copy()
            ts_df['minute'] = ts_df['ts'].dt.floor('min')
            per_min = ts_df.groupby('minute').size().reset_index(name='events')
            line = alt.Chart(per_min).mark_line(point=True).encode(
                x='minute:T', y='events:Q'
            )
            st.altair_chart(line, use_container_width=True)
        else:
            st.info("Sin datos de tiempo disponibles. Los logs no contienen fechas.")

    if show_raw:
        st.subheader("Eventos crudos (primeros 500)")
        st.dataframe(df_events.head(500), use_container_width=True)


if __name__ == "__main__":
    main()
