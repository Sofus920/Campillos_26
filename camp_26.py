import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- Konfiguration ---
st.set_page_config(page_title="Campillos 30H Dashboard",
                   layout="wide", initial_sidebar_state="expanded")

# --- Custom CSS for et bedre design ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { color: #1e293b; font-weight: 700; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    </style>
""", unsafe_allow_html=True)

# --- Data Indlæsning ---


@st.cache_data
def load_data():
    df = pd.read_excel("Camp_26.xlsx")

    def parse_time(t_str):
        try:
            parts = str(t_str).split(':')
            if len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            return np.nan
        except:
            return np.nan

    df['Sekunder'] = df['Omgangstid'].apply(parse_time)
    df['Kumulativ_Tid_Sek'] = df.groupby('Hold')['Sekunder'].cumsum()
    df['Timer_Kørt'] = df['Kumulativ_Tid_Sek'] / 3600

    def get_direction(hrs):
        if 15 <= hrs < 24:
            return 'Baglæns'
        return 'Forlæns'
    df['Retning'] = df['Timer_Kørt'].apply(get_direction)

    df['Hold_Nr'] = df['Hold'].str.extract(r'^(\d+)').astype(float)
    df['Kategori'] = np.where(df['Hold_Nr'] >= 35, 'Masters', 'Standard')

    hold_rang = df.groupby('Hold').size().sort_values(
        ascending=False).reset_index()
    hold_rang['Placering'] = hold_rang.index + 1
    df = df.merge(hold_rang[['Hold', 'Placering']], on='Hold', how='left')

    master_rang = df[df['Kategori'] == 'Masters'].groupby(
        'Hold').size().sort_values(ascending=False).reset_index()
    master_rang['Master_Placering'] = master_rang.index + 1
    df = df.merge(
        master_rang[['Hold', 'Master_Placering']], on='Hold', how='left')

    df['Er_Pit'] = df['Sekunder'] > 105
    df['Ny_Stint'] = df['Er_Pit'] | (df['Kører Navn'] != df['Kører Navn'].shift()) | (
        df['Hold'] != df['Hold'].shift())
    df['Stint_ID'] = df['Ny_Stint'].cumsum()
    df['Time_Bucket'] = np.floor(df['Timer_Kørt'])

    return df


df = load_data()

# --- UI Setup ---
st.title("🏎️ Campillos 30H 2026 - Data Dashboard")
st.markdown("Dybdegående analyse af track pace, konsistens, pit-strategi og stints. **Analysér data omgang for omgang.**")
st.markdown("---")

# --- Sidebar Filtre ---
st.sidebar.markdown(
    "<div style='text-align: center; font-size: 70px; margin-bottom: -20px;'>🏎️</div>", unsafe_allow_html=True)
st.sidebar.header("⚙️ Indstillinger")

kategori_valg = st.sidebar.radio(
    "🏁 Hold Kategori", ["Alle", "Standard (1-34)", "Masters (35+)"])

if kategori_valg == "Standard (1-34)":
    alle_hold = sorted(df[df['Kategori'] == 'Standard']['Hold'].unique())
elif kategori_valg == "Masters (35+)":
    alle_hold = sorted(df[df['Kategori'] == 'Masters']['Hold'].unique())
else:
    alle_hold = sorted(df['Hold'].unique())

valgte_hold = st.sidebar.multiselect("🏎️ Vælg hold til analyse", alle_hold, default=[
                                     h for h in ["20 - SALLIE'S PRO", "2 - NEO LEVEL"] if h in alle_hold])
valgt_retning = st.sidebar.radio(
    "🔄 Baneretning", ["Begge", "Forlæns", "Baglæns"])

st.sidebar.markdown("---")
maks_tid = st.sidebar.slider("⏱️ Pace Cut-off (Maks tilladt omgangstid)", min_value=85.0, max_value=120.0,
                             value=95.0, step=0.5, help="Fjerner safety cars og vending af bane fra jeres pace.")
benchmark_valg = st.sidebar.selectbox("📊 Stint Benchmark (SoF)", [
                                      "Vinder (P1)", "Top 3", "Top 5", "Top 10", "Top 20", "Alle hold", "Vinder Masters", "Top 3 Masters", "Top 5 Masters"], index=2)

df_filtered = df[df['Hold'].isin(valgte_hold)]
if valgt_retning != "Begge":
    df_filtered = df_filtered[df_filtered['Retning'] == valgt_retning]

df_clean = df_filtered[df_filtered['Sekunder'] <= maks_tid].copy()
df_all_clean = df[df['Sekunder'] <= maks_tid].copy()

# Beregn Alle Køreres Personlige Pace (til Strength of Field) ud fra RÅ tider pr. RETNING
driver_personal_pace = df_all_clean.groupby(['Hold', 'Kører Navn', 'Retning'])[
    'Sekunder'].median().reset_index().rename(columns={'Sekunder': 'Personal_Pace'})

# --- Beregn Benchmark Pace for Relativ Pace Analyse ---
if benchmark_valg == "Vinder (P1)":
    bench_teams = df[df['Placering'] == 1]['Hold'].unique()
elif benchmark_valg == "Top 3":
    bench_teams = df[df['Placering'] <= 3]['Hold'].unique()
elif benchmark_valg == "Top 5":
    bench_teams = df[df['Placering'] <= 5]['Hold'].unique()
elif benchmark_valg == "Top 10":
    bench_teams = df[df['Placering'] <= 10]['Hold'].unique()
elif benchmark_valg == "Top 20":
    bench_teams = df[df['Placering'] <= 20]['Hold'].unique()
elif benchmark_valg == "Vinder Masters":
    bench_teams = df[df['Master_Placering'] == 1]['Hold'].unique()
elif benchmark_valg == "Top 3 Masters":
    bench_teams = df[df['Master_Placering'] <= 3]['Hold'].unique()
elif benchmark_valg == "Top 5 Masters":
    bench_teams = df[df['Master_Placering'] <= 5]['Hold'].unique()
else:
    bench_teams = df['Hold'].unique()

bench_df = df_all_clean[df_all_clean['Hold'].isin(bench_teams)]
bench_pace = bench_df.groupby('Time_Bucket')['Sekunder'].median(
).reset_index().rename(columns={'Sekunder': 'Benchmark_Pace'})

df_clean = df_clean.merge(bench_pace, on='Time_Bucket', how='left')
df_clean['Relativ_Pace_Lap'] = df_clean['Sekunder'] - \
    df_clean['Benchmark_Pace']

# Gør det samme for det samlede felt (så vi kan rangere alle efter Relativ Pace)
df_all_clean = df_all_clean.merge(bench_pace, on='Time_Bucket', how='left')
df_all_clean['Relativ_Pace_Lap'] = df_all_clean['Sekunder'] - \
    df_all_clean['Benchmark_Pace']

# --- Faner ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    ["📊 Hold Sammenligning", "👤 Kører Analyse", "🔧 Pit-tider", "⏱️ Stint Analyse (SoF)", "🏆 Hele Feltet", "⚔️ Head-to-Head", "🔍 Kører Detaljer"])

# Farvelogik til tabeller


def color_delta(val):
    if isinstance(val, (int, float)) and not pd.isna(val):
        if val < 0:
            return 'color: #15803d; font-weight: bold;'
        elif val > 0:
            return 'color: #b91c1c; font-weight: bold;'
    return ''


def color_laps(val):
    if isinstance(val, (int, float)) and not pd.isna(val):
        if val >= 150:
            return 'background-color: #16a34a; color: white;'  # Mørkegrøn
        elif val >= 80:
            return 'background-color: #86efac; color: black;'  # Lysegrøn
        elif val >= 40:
            return 'background-color: #fef08a; color: black;'  # Gul
        else:
            return 'background-color: #fca5a5; color: black;'  # Rød
    return ''


# TAB 1: Hold
with tab1:
    st.subheader("Overordnet Hold Pace")
    if not df_clean.empty:
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric(label="Hurtigste Omgang (Valgte hold)",
                      value=f"{df_clean['Sekunder'].min():.3f} sek")
        with kpi2:
            st.metric(label="Gennemsnitlig Median Pace",
                      value=f"{df_clean['Sekunder'].median():.3f} sek")
        with kpi3:
            st.metric(label="Totale Omgange Analyseret",
                      value=f"{len(df_clean)}")

        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            fig_pace = px.box(df_clean, x='Hold', y='Sekunder', color='Hold',
                              title="Pace Fordeling (Rå omgangstider, Boxplot)", template="plotly_white")
            fig_pace.update_yaxes(title="Omgangstid (Sekunder)")
            st.plotly_chart(fig_pace, use_container_width=True)

# TAB 2: Kørere
with tab2:
    st.subheader("Individuel Kører Pace & Relativ Styrke")
    st.markdown(
        f"*Kørernes Pace Forlæns og Baglæns vises nu hver for sig. Ranglisten sorteres automatisk efter **Relativ_Pace_Gns** (tidsgabet til {benchmark_valg} pr. omgang), da dette er den mest fair indikator for overall performance på tværs af banens retninger.*")
    st.info("💡 **Datagrundlag (Farvekode):** Kolonnen for antal omgange er farvekodet for at vise datasikkerheden. **Mørkegrøn** (>150 omgange) = Meget stærkt datagrundlag, **Lysegrøn** (80-150 omgange) = Solidt, **Gul** (40-80 omgange) = Usikkert, **Rød** (<40 omgange) = For lille grundlag til en endelig konklusion.")

    if not df_clean.empty:
        if valgt_retning == "Begge":
            pivot = df_clean.pivot_table(index=['Hold', 'Kører Navn'], columns='Retning', values='Sekunder', aggfunc={
                                         'Sekunder': ['count', 'median']})
            pivot.columns = ['_'.join(col).strip()
                             for col in pivot.columns.values]
            pivot = pivot.reset_index()

            overall = df_clean.groupby(['Hold', 'Kører Navn']).agg(
                Totale_Omgange=('Sekunder', 'count'),
                Relativ_Pace_Gns=('Relativ_Pace_Lap', 'median')
            ).reset_index()

            driver_stats = overall.merge(pivot, on=['Hold', 'Kører Navn'])
            rename_dict = {'count_Forlæns': 'Omg_Forlæns', 'count_Baglæns': 'Omg_Baglæns',
                           'median_Forlæns': 'Pace_Forlæns', 'median_Baglæns': 'Pace_Baglæns'}
            driver_stats = driver_stats.rename(columns=rename_dict)

            for col in ['Omg_Forlæns', 'Omg_Baglæns', 'Pace_Forlæns', 'Pace_Baglæns']:
                if col not in driver_stats.columns:
                    driver_stats[col] = np.nan
        else:
            driver_stats = df_clean.groupby(['Hold', 'Kører Navn']).agg(
                Totale_Omgange=('Sekunder', 'count'),
                Pace=('Sekunder', 'median'),
                Relativ_Pace_Gns=('Relativ_Pace_Lap', 'median')
            ).reset_index()

        driver_stats = driver_stats[driver_stats['Totale_Omgange'] >= 10].sort_values(
            'Relativ_Pace_Gns').reset_index(drop=True)
        driver_stats.index = driver_stats.index + 1

        format_dict = {
            col: '{:.3f}' for col in driver_stats.columns if 'Pace' in col}
        format_dict['Relativ_Pace_Gns'] = '{:+.3f} sek'

        lap_cols = [c for c in driver_stats.columns if 'Omg' in c]

        with st.container(border=True):
            st.dataframe(driver_stats.style.map(color_delta, subset=['Relativ_Pace_Gns']).map(
                color_laps, subset=lap_cols).format(format_dict, na_rep="-"), use_container_width=True)

# TAB 3: Pit
with tab3:
    st.subheader("Samlet Reelt Tidstab i Pitten")
    if not df_filtered.empty:
        team_median_lap = df_all_clean.groupby('Hold')['Sekunder'].median(
        ).reset_index().rename(columns={'Sekunder': 'Normal_Lap'})
        df_pit = df[df['Er_Pit']].merge(team_median_lap, on='Hold')
        df_pit['Pit_Loss_Sek'] = df_pit['Sekunder'] - df_pit['Normal_Lap']

        pit_summary = df_pit[df_pit['Hold'].isin(valgte_hold)].groupby('Hold').agg(Antal_Pitstops=(
            'Er_Pit', 'count'), Samlet_Tidstab_Min=('Pit_Loss_Sek', lambda x: x.sum() / 60)).reset_index()

        with st.container(border=True):
            fig_pit = px.bar(pit_summary, x='Hold', y='Samlet_Tidstab_Min', color='Hold',
                             text_auto='.1f', title="Minutter tabt i pitten i alt", template="plotly_white")
            st.plotly_chart(fig_pit, use_container_width=True)

# TAB 4: Stint Analyse
with tab4:
    st.subheader("Konkurrence-analyse, Varians & Strength of Field")
    st.info("ℹ️ Et stint deles automatisk hvis omgangstiden overstiger jeres 'Pace Cut-off' (f.eks. ved gult flag, safety car eller banevending). Pit-ind omgange er automatisk renset fra statistikken.")

    if len(valgte_hold) > 0:
        hovedhold = valgte_hold[0]
        team_df = df_clean[df_clean['Hold'] == hovedhold].copy()

        if not team_df.empty:
            stint_counts = team_df.groupby('Stint_ID').size()
            valid_stints = stint_counts[stint_counts > 5].index
            pit_in_laps = team_df[team_df['Stint_ID'].isin(
                valid_stints)].groupby('Stint_ID').tail(1).index
            team_df_clean_stints = team_df.drop(pit_in_laps)

            stint_summary = team_df_clean_stints.groupby('Stint_ID').agg(
                Kører=('Kører Navn', 'first'),
                Retning=('Retning', 'first'),
                Antal_Omgange=('Sekunder', 'count'),
                Stint_Start_Time=('Timer_Kørt', 'min'),
                Stint_End_Time=('Timer_Kørt', 'max'),
                Stint_Pace=('Sekunder', 'median'),
                Hurtigste_Omgang=('Sekunder', 'min'),
                Stabilitet_StdDev=('Sekunder', 'std'),
                Varians=('Sekunder', 'var'),
                Stint_Delta=('Relativ_Pace_Lap', 'median')
            ).reset_index()

            stint_summary = stint_summary[stint_summary['Antal_Omgange'] >= 5].sort_values(
                'Stint_Start_Time').reset_index(drop=True)
            stint_summary['Stint_Nr'] = stint_summary.index + 1

            sof_list = []
            rank_list = []

            for _, row in stint_summary.iterrows():
                start_t, end_t = row['Stint_Start_Time'], row['Stint_End_Time']
                direction = row['Retning']

                everyone_on_track = df_all_clean[(df_all_clean['Timer_Kørt'] >= start_t) & (
                    df_all_clean['Timer_Kørt'] <= end_t)]

                opponents_on_track = everyone_on_track[everyone_on_track['Hold'] != hovedhold]
                unique_opps = opponents_on_track[[
                    'Hold', 'Kører Navn']].drop_duplicates()
                if not unique_opps.empty:
                    opp_paces = unique_opps.merge(driver_personal_pace[driver_personal_pace['Retning'] == direction], on=[
                                                  'Hold', 'Kører Navn'], how='inner')
                    sof_list.append(opp_paces['Personal_Pace'].mean())
                else:
                    sof_list.append(np.nan)

                current_paces = everyone_on_track.groupby(['Hold', 'Kører Navn']).agg(
                    Laps=('Sekunder', 'count'), Pace=('Sekunder', 'median')).reset_index()
                valid_paces = current_paces[current_paces['Laps'] >= 3].sort_values(
                    'Pace').reset_index(drop=True)
                valid_paces['Rank'] = valid_paces.index + 1

                driver_rank_row = valid_paces[(valid_paces['Hold'] == hovedhold) & (
                    valid_paces['Kører Navn'] == row['Kører'])]
                total_drivers = len(valid_paces)

                if not driver_rank_row.empty:
                    d_rank = driver_rank_row['Rank'].iloc[0]
                    rank_list.append(f"{d_rank} / {total_drivers}")
                else:
                    rank_list.append(f"- / {total_drivers}")

            stint_summary['SoF_Modstandernes_Niveau'] = sof_list
            stint_summary['Track_Rangering'] = rank_list
            stint_summary['Graf_Tekst'] = stint_summary['Kører'] + \
                " (" + stint_summary['Track_Rangering'] + ")"

            display_stints = stint_summary[['Stint_Nr', 'Kører', 'Stint_Start_Time', 'Antal_Omgange', 'Stint_Pace',
                                            'Hurtigste_Omgang', 'Track_Rangering', 'Stabilitet_StdDev', 'Varians', 'Stint_Delta', 'SoF_Modstandernes_Niveau']].copy()
            display_stints['Stint_Start_Time'] = display_stints['Stint_Start_Time'].apply(
                lambda x: f"Time {int(x)}")

            with st.container(border=True):
                st.markdown(
                    f"**Detaljeret Stint Oversigt for {hovedhold}** (Sammenlignet mod {benchmark_valg})")
                st.markdown(
                    "*(**Track Rangering** viser din placering baseret på median-pace blandt alle 47 hold, der delte banen med dig i præcis dette tidsrum).*")
                st.dataframe(display_stints.style.map(color_delta, subset=['Stint_Delta']).format({
                    'Stint_Pace': '{:.3f}', 'Hurtigste_Omgang': '{:.3f}', 'Stabilitet_StdDev': '{:.3f}', 'Varians': '{:.3f}',
                    'Stint_Delta': '{:+.3f} sek', 'SoF_Modstandernes_Niveau': '{:.3f} sek'
                }), use_container_width=True, hide_index=True)

            stint_summary['Farve'] = np.where(
                stint_summary['Stint_Delta'] > 0, 'Langsommere (Rød)', 'Hurtigere (Grøn)')
            with st.container(border=True):
                fig_delta = px.bar(stint_summary, x='Stint_Nr', y='Stint_Delta', color='Farve',
                                   color_discrete_map={
                                       'Langsommere (Rød)': '#ef4444', 'Hurtigere (Grøn)': '#22c55e'},
                                   text='Graf_Tekst', title=f"Tidsgab til Benchmark pr. Stint (Labels viser Track Rangering i stintet)", template="plotly_white")
                fig_delta.update_traces(
                    textposition='outside', textfont_size=10, textangle=-90)
                fig_delta.update_yaxes(
                    autorange="reversed", title="Delta Pace (Sekunder)")
                fig_delta.update_xaxes(
                    tickmode='linear', tick0=1, dtick=1, title="Stint Nummer")
                st.plotly_chart(fig_delta, use_container_width=True)

# TAB 5: Hele feltet
with tab5:
    st.subheader(f"Rangliste: Hele Feltet ({kategori_valg})")
    st.markdown(
        "*Kørernes Pace Forlæns og Baglæns vises nu hver for sig. Ranglisten sorteres automatisk efter den overordnede **Relativ_Pace_Gns** (tidsgabet til {benchmark_valg} pr. omgang).*")
    st.info("💡 **Datagrundlag (Farvekode):** Kolonnen for antal omgange er farvekodet for at vise datasikkerheden. **Mørkegrøn** (>150 omgange) = Meget stærkt datagrundlag, **Lysegrøn** (80-150 omgange) = Solidt, **Gul** (40-80 omgange) = Usikkert, **Rød** (<40 omgange) = For lille grundlag.")

    if kategori_valg == "Standard (1-34)":
        df_tab5 = df_all_clean[df_all_clean['Kategori'] == 'Standard']
    elif kategori_valg == "Masters (35+)":
        df_tab5 = df_all_clean[df_all_clean['Kategori'] == 'Masters']
    else:
        df_tab5 = df_all_clean

    if valgt_retning != "Begge":
        df_tab5 = df_tab5[df_tab5['Retning'] == valgt_retning]

    if not df_tab5.empty:
        if valgt_retning == "Begge":
            pivot = df_tab5.pivot_table(index=['Hold', 'Kører Navn'], columns='Retning', values='Sekunder', aggfunc={
                                        'Sekunder': ['count', 'median']})
            pivot.columns = ['_'.join(col).strip()
                             for col in pivot.columns.values]
            pivot = pivot.reset_index()

            overall = df_tab5.groupby(['Hold', 'Kører Navn']).agg(
                Totale_Omgange=('Sekunder', 'count'),
                Relativ_Pace_Gns=('Relativ_Pace_Lap', 'median')
            ).reset_index()

            all_drivers_stats = overall.merge(pivot, on=['Hold', 'Kører Navn'])
            rename_dict = {'count_Forlæns': 'Omg_Forlæns', 'count_Baglæns': 'Omg_Baglæns',
                           'median_Forlæns': 'Pace_Forlæns', 'median_Baglæns': 'Pace_Baglæns'}
            all_drivers_stats = all_drivers_stats.rename(columns=rename_dict)

            for col in ['Omg_Forlæns', 'Omg_Baglæns', 'Pace_Forlæns', 'Pace_Baglæns']:
                if col not in all_drivers_stats.columns:
                    all_drivers_stats[col] = np.nan
        else:
            all_drivers_stats = df_tab5.groupby(['Hold', 'Kører Navn']).agg(
                Totale_Omgange=('Sekunder', 'count'),
                Pace=('Sekunder', 'median'),
                Relativ_Pace_Gns=('Relativ_Pace_Lap', 'median')
            ).reset_index()

        all_drivers_stats = all_drivers_stats[all_drivers_stats['Totale_Omgange'] >= 10].sort_values(
            'Relativ_Pace_Gns').reset_index(drop=True)
        all_drivers_stats.index = all_drivers_stats.index + 1

        format_dict = {
            col: '{:.3f}' for col in all_drivers_stats.columns if 'Pace' in col}
        format_dict['Relativ_Pace_Gns'] = '{:+.3f} sek'

        lap_cols = [c for c in all_drivers_stats.columns if 'Omg' in c]

        with st.container(border=True):
            st.dataframe(all_drivers_stats.style.map(color_delta, subset=['Relativ_Pace_Gns']).map(
                color_laps, subset=lap_cols).format(format_dict, na_rep="-"), use_container_width=True)

# TAB 6: Head-to-Head
with tab6:
    st.subheader("⚔️ Head-to-Head: Løbende Track Pace (Uden pit-tider)")
    st.markdown("Her sammenlignes jeres rene pace **omgang for omgang**, og pit-tiderne er filtreret HELT væk. \n* Hvis kurven går **OP**, kørte modstanderen stærkere end jer.\n* Hvis kurven går **NED**, kørte I stærkere og hentede tid på dem.")

    with st.container(border=True):
        col1, col2 = st.columns(2)
        h2h_team1 = col1.selectbox("Vælg dit hold (Hold A)", alle_hold, index=alle_hold.index(
            "20 - SALLIE'S PRO") if "20 - SALLIE'S PRO" in alle_hold else 0)
        h2h_team2 = col2.selectbox("Vælg modstander (Hold B)", alle_hold, index=alle_hold.index(
            "2 - NEO LEVEL") if "2 - NEO LEVEL" in alle_hold else min(1, len(alle_hold)-1))

        if h2h_team1 and h2h_team2:
            t1_data = df[df['Hold'] == h2h_team1].copy().reset_index(drop=True)
            t2_data = df[df['Hold'] == h2h_team2].copy().reset_index(drop=True)

            norm_T1 = df_all_clean[df_all_clean['Hold']
                                   == h2h_team1]['Sekunder'].median()
            norm_T2 = df_all_clean[df_all_clean['Hold']
                                   == h2h_team2]['Sekunder'].median()

            t1_data['Pit_Loss'] = np.where(
                t1_data['Er_Pit'], t1_data['Sekunder'] - norm_T1, 0)
            t2_data['Pit_Loss'] = np.where(
                t2_data['Er_Pit'], t2_data['Sekunder'] - norm_T2, 0)

            t1_data['Kumulativ_Pit_Loss'] = t1_data['Pit_Loss'].cumsum()
            t2_data['Kumulativ_Pit_Loss'] = t2_data['Pit_Loss'].cumsum()

            t1_data['Lap_Nr'] = t1_data.index + 1
            t2_data['Lap_Nr'] = t2_data.index + 1

            h2h = pd.merge(t1_data[['Lap_Nr', 'Kumulativ_Tid_Sek', 'Timer_Kørt', 'Er_Pit', 'Kører Navn', 'Kumulativ_Pit_Loss']],
                           t2_data[['Lap_Nr', 'Kumulativ_Tid_Sek', 'Timer_Kørt',
                                    'Er_Pit', 'Kører Navn', 'Kumulativ_Pit_Loss']],
                           on='Lap_Nr', suffixes=('_T1', '_T2'))

            h2h['Samlet_Tidsgab'] = h2h['Kumulativ_Tid_Sek_T1'] - \
                h2h['Kumulativ_Tid_Sek_T2']
            h2h['Track_Tidsgab'] = h2h['Samlet_Tidsgab'] - \
                (h2h['Kumulativ_Pit_Loss_T1'] - h2h['Kumulativ_Pit_Loss_T2'])

            fig_gap = px.line(h2h, x='Timer_Kørt_T1', y='Track_Tidsgab',
                              title=f"Ren Pace Udvikling på Banen: {h2h_team1} mod {h2h_team2}",
                              labels={'Timer_Kørt_T1': 'Timer kørt i løbet',
                                      'Track_Tidsgab': 'Pace Tidsgab (Sekunder)'},
                              template="plotly_white", color_discrete_sequence=['#3b82f6'])

            pits_t1 = h2h[h2h['Er_Pit_T1']]
            fig_gap.add_scatter(x=pits_t1['Timer_Kørt_T1'], y=pits_t1['Track_Tidsgab'], mode='markers',
                                marker=dict(color='#ef4444', size=10, symbol='circle', line=dict(
                                    width=1, color='white')),
                                name=f'Pitstops {h2h_team1}', hovertext=pits_t1['Kører Navn_T1'] + " pitter her")

            pits_t2 = h2h[h2h['Er_Pit_T2']]
            fig_gap.add_scatter(x=pits_t2['Timer_Kørt_T1'], y=pits_t2['Track_Tidsgab'], mode='markers',
                                marker=dict(color='#f59e0b', size=10, symbol='diamond', line=dict(
                                    width=1, color='white')),
                                name=f'Pitstops {h2h_team2}', hovertext=pits_t2['Kører Navn_T2'] + " pitter her")

            st.plotly_chart(fig_gap, use_container_width=True)

# TAB 7: Kører Detaljer
with tab7:
    st.subheader("🔍 Detaljeret Kører & Stint Udforskning")
    st.markdown("Dyk ned i de enkelte stints for at analysere brændstofforbrænding (trendlinje), trafik og personlig konsistens omgang for omgang.")
    st.info("💡 **Bemærk:** Pit-ind omgangen (den allersidste omgang i stintet) er automatisk fjernet fra denne visning, så den ikke skævvrider jeres pace-udvikling og fejl-tæller.")

    with st.container(border=True):
        d_col1, d_col2 = st.columns(2)
        t7_team = d_col1.selectbox(
            "Vælg Hold", valgte_hold, key='t7_team_select')

        if t7_team:
            team_drivers = df_clean[df_clean['Hold']
                                    == t7_team]['Kører Navn'].unique()
            t7_driver = d_col2.selectbox(
                "Vælg Kører", team_drivers, key='t7_driver_select')

            if t7_driver:
                driver_stints = df_clean[(df_clean['Hold'] == t7_team) & (
                    df_clean['Kører Navn'] == t7_driver)].copy()

                stint_summary_t7 = driver_stints.groupby('Stint_ID').agg(
                    Start_Time=('Timer_Kørt', 'min'),
                    Laps=('Sekunder', 'count')
                ).reset_index()

                stint_summary_t7 = stint_summary_t7[stint_summary_t7['Laps'] >= 5].sort_values(
                    'Start_Time')
                stint_summary_t7['Stint_Label'] = stint_summary_t7.apply(
                    lambda r: f"Stint (Start: Time {int(r['Start_Time'])} | {int(r['Laps'])} omgange)", axis=1)

                if not stint_summary_t7.empty:
                    t7_stint_label = st.selectbox(
                        "Vælg et specifikt stint at analysere", stint_summary_t7['Stint_Label'].tolist())
                    selected_stint_id = stint_summary_t7[stint_summary_t7['Stint_Label']
                                                         == t7_stint_label]['Stint_ID'].iloc[0]

                    stint_data = driver_stints[driver_stints['Stint_ID'] == selected_stint_id].copy(
                    )
                    stint_data = stint_data.sort_values(
                        'Timer_Kørt').reset_index(drop=True)

                    if len(stint_data) > 5:
                        stint_data = stint_data.iloc[:-1]

                    stint_data['Omgang_I_Stint'] = stint_data.index + 1

                    median_pace = stint_data['Sekunder'].median()
                    std_dev = stint_data['Sekunder'].std()
                    traffic_threshold = median_pace + 1.5
                    traffic_laps = len(
                        stint_data[stint_data['Sekunder'] > traffic_threshold])

                    n_laps = len(stint_data)
                    q_size = max(3, n_laps // 4)
                    start_pace = stint_data.head(q_size)['Sekunder'].median()
                    end_pace = stint_data.tail(q_size)['Sekunder'].median()
                    pace_udvikling = end_pace - start_pace

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Median Pace", f"{median_pace:.3f} sek")
                    m2.metric("Stabilitet (StdDev)", f"{std_dev:.3f} sek",
                              help="Lavere er bedre. Angiver udsvinget i omgangstider.")
                    m3.metric("Trafik / Fejl Omgange", f"{traffic_laps}",
                              help="Antal omgange der er mere end 1.5 sek langsommere end medianen.")
                    m4.metric("Pace Udvikling (Slut vs Start)", f"{pace_udvikling:+.3f} sek", delta_color="inverse",
                              help="Sammenligner medianen af de første og sidste omgange i stintet. Minus (Grøn) betyder at køreren blev hurtigere mod slutningen (f.eks. pga. brændstof).")

                    stint_data['Rullende_Gns'] = stint_data['Sekunder'].rolling(
                        window=max(3, n_laps//8), center=True).mean()

                    fig_stint = px.scatter(stint_data, x='Omgang_I_Stint', y='Sekunder',
                                           title=f"Omgangstider for {t7_driver} - {t7_stint_label}",
                                           labels={
                                               'Omgang_I_Stint': 'Omgang nr. i stintet', 'Sekunder': 'Omgangstid (sek)'},
                                           template="plotly_white", color_discrete_sequence=['#3b82f6'])

                    fig_stint.add_trace(go.Scatter(x=stint_data['Omgang_I_Stint'], y=stint_data['Rullende_Gns'],
                                                   mode='lines', name='Trend (Rullende Gns)', line=dict(color='#ef4444', width=3)))

                    fig_stint.add_hline(y=median_pace, line_dash="dash", line_color="green",
                                        annotation_text="Median Pace", annotation_position="bottom right")

                    st.plotly_chart(fig_stint, use_container_width=True)
                else:
                    st.warning(
                        "Ingen gyldige stints fundet for denne kører (kræver min. 5 omgange uden pit).")
