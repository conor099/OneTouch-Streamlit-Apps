#%% Imports.
import urllib
import streamlit as st
import sqlalchemy as alc
import pandas as pd
import altair as alt

#%% Connect to SQL server using SQL alchemy.

def connect_to_sql_alchemy_server():
    """
    :param   server:    Name of SQL server you want to connect to.
    :param   database:  Name of database you want to connect to.
    :param   username:  Azure account username.
    :return: engine:    SQL alchemy engine connected to desired SQL server.
    """
    # Input server, database, and username.
    server = st.secrets["server"]
    database = st.secrets["database"]
    username = st.secrets["username"]
    password = st.secrets["password"]

    # Connection to server/database.
    params = urllib.parse.quote_plus('DRIVER={ODBC Driver 17 for SQL Server};'
                                     f'SERVER=tcp:{server},1433;'
                                     f'DATABASE={database};'
                                     f'UID={username};'
                                     f'PWD={password}')
    conn_string = "mssql+pyodbc:///?odbc_connect={}".format(params)

    # Foreign SQL server can't handle all rows being inserted at once, so fast_executemany is set to False.
    engine = alc.create_engine(conn_string, echo=False, pool_pre_ping=True)
    print("Now connected to server")

    return engine

#%% Function to load latest game date.

@st.cache_data(ttl=600)
def load_latest_game_date():
    """
    :return: Date of the latest game included in the dataframe.
    """
    # Connect to SQL server.
    sql_engine = connect_to_sql_alchemy_server()

    # Select latest game date.
    query = """
                SELECT
                    MAX(game_date) AS latest_game_date
                FROM streamlit.Fbref_Appearances
    """

    # Convert query to date.
    latest_game_date = pd.read_sql(query, sql_engine)["latest_game_date"].iloc[0]

    return latest_game_date

#%% Function to load all unique competition names.

@st.cache_data(ttl=600)
def load_competitions():
    """
    :return: List containing all unique competition names.
    """
    # Connect to SQL server.
    sql_engine = connect_to_sql_alchemy_server()

    # Select all distinct competitions names.
    query = """
                SELECT DISTINCT
                    competition_name
                FROM streamlit.Fbref_Appearances
    """

    # Convert query to list.
    competitions = pd.read_sql(query, sql_engine)["competition_name"].tolist()

    return competitions

#%% Function to load the minimum and maximum number of seasons a player has played in a selected competition(s).

@st.cache_data(ttl=600)
def load_number_of_seasons(selected_comps):
    """
    :param selected_comps: List of competition names as selected in previous filter.
    :return: Minimum and maximum number of seasons in selected competition(s).
    """
    # Return empty list if no competition selected.
    if not selected_comps:
        return []

    # Connect to SQL server.
    sql_engine = connect_to_sql_alchemy_server()

    # Create a string of ?s, followed by a comma, the ?s will be replaced by the selected competitions. SQL Server uses ? placeholders.
    placeholders = ",".join(["?"] * len(selected_comps))

    # SQL query for unique players.
    query = f"""
        SELECT
            MAX(number_of_seasons) AS max_seasons
        FROM streamlit.Fbref_Appearances
        WHERE competition_name IN ({placeholders})
    """

    # Create dataframe using SQL query. The ?s are replaced by the selected competitions defined in params.
    df = pd.read_sql(query, sql_engine, params=tuple(selected_comps))

    # Extract max seasons that one player has played in selected competitions.
    max_seasons = int(df.iloc[0]["max_seasons"])

    return max_seasons

#%% Function to load all unique players based on the competition selected.

@st.cache_data(ttl=600)
def load_players(minimum_seasons, selected_comps):
    """
    :param minimum_seasons: Minimum number of seasons that a player must have played in selected competition(s).
    :param selected_comps: List of competition names as selected in previous filter.
    :return: List of unique players names based on competition names that were selected.
    """
    # Return empty list if no competition selected.
    if not selected_comps:
        return []

    # Connect to SQL server.
    sql_engine = connect_to_sql_alchemy_server()

    # Create a string of ?s, followed by a comma, the ?s will be replaced by the selected competitions. SQL Server uses ? placeholders.
    placeholders = ",".join(["?"] * len(selected_comps))

    # SQL query for unique players.
    query = f"""
        SELECT DISTINCT
            player_name
        FROM streamlit.Fbref_Appearances
        WHERE number_of_seasons >= ?
           AND competition_name IN ({placeholders})
    """

    # Create dataframe using SQL query. The ?s are replaced by the selected competitions defined in params.
    df = pd.read_sql(query, sql_engine, params=(minimum_seasons, *selected_comps))

    # Sort dataframe and convert to list.
    players = sorted(df["player_name"].tolist())

    return players

#%% Function to load the player dataframe based on the competitions and player selected.

@st.cache_data(ttl=600)
def load_player_data(minimum_seasons, player, selected_comps):
    """
    :param minimum_seasons: Minimum number of seasons that a player must have played in selected competition(s).
    :param player: Player as selected in previous filter.
    :param selected_comps: List of competition names as selected in previous filter.
    :return: Dataframe containing data on the selected player in the selected competition(s).
    """
    # Return empty dataframe if player or competitions not selected.
    if not player or not selected_comps:
        return pd.DataFrame()

    # Connect to SQL server.
    sql_engine = connect_to_sql_alchemy_server()

    # Create a string of ?s, followed by a comma, the ?s will be replaced by the selected competitions. SQL Server uses ? placeholders.
    placeholders = ",".join(["?"] * len(selected_comps))

    # SQL query dataframe for selected player and competition(s).
    query = f"""
        SELECT *
        FROM streamlit.Fbref_Appearances
        WHERE number_of_seasons >= ?
          AND player_name = ?
          AND competition_name IN ({placeholders})
    """
    # Create dataframe from query. First ? is selected player, the following are the selected competition(s).
    df = pd.read_sql(query, sql_engine, params=(minimum_seasons, player, *selected_comps))

    return df


#%% Build Streamlit app.

def create_streamlit_app():
    """
    :return:
    """
    # Set up page configuration.
    st.set_page_config(
        page_title="Players in European Competitions",
        page_icon="C:/Users/conor/OneDrive/Desktop/OneTouch/Images/Logo_Youtube.png",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Report a bug': "mailto:contact@onetouchinsights.com",
            'About': "All data comes from Fbref European matches from 1990-2025. 2 seasons of European Cup (1990-1992), "
                     "34 seasons of Champions League (1992-2025), 20 seasons of UEFA Cup (1990-2009), 16 seasons of "
                     "Europa League (2010-2025), and 4 seasons of Europa Conference League (2021-2025)."
        }
    )

    # Add latest game date in dataframe as a header.
    st.markdown(f"<h1 style='color: #FF800E; font-size:8px;'>Latest game date: {load_latest_game_date().strftime('%B %d, %Y')}</h1>", unsafe_allow_html=True)
    # st.header(f"Latest game date: {load_latest_game_date().strftime('%B %d, %Y')}")

    # Set title.
    st.markdown("<h1 style='text-align: center; color: #FF800E;'>⚽ European Competitions: Player overview ⚽</h1>",
                unsafe_allow_html=True)

    # Wrap all filters in a box.
    with st.container(border=True):
        # Step 1: Select competitions.
        competitions = st.multiselect(
            "Select a competition/competitions:",
            options=sorted(load_competitions()),
            default="Champions League"
        )

        # Raise error if no competition selected.
        if not competitions:
            st.error("Please select at least one competition.")
            return

        # Step 2: Select minimum number of seasons a player must have played in the competition.
        max_seasons = load_number_of_seasons(competitions)
        minimum_seasons = st.slider(
            label="Select minimum number of seasons:",
            min_value=1,
            max_value=max_seasons,
            value=3 # Default value.
        )

        # Step 3: Select player.
        players = load_players(minimum_seasons, competitions)
        player = st.selectbox("Select a player:", players)

        # Raise error if no player selected.
        if not player:
            st.error("Please select a player.")
            return

        # Step 4: Load player data.
        player_df = load_player_data(minimum_seasons, player, competitions)

        # Raise error if a selected player has not made at least one appearance in the selected competition.
        if player_df.empty:
            st.warning("No data available for this player in the selected competitions.")
            return

        # Step 4: Season filter.
        seasons = st.multiselect(
            "(Optional) Select a season/seasons:",
            options=sorted(player_df["season_name"].unique(), reverse=True)
        )

        # If no season is selected, show stats for all seasons for the player. Otherwise, filter the dataframe.
        if seasons:
            final_df = player_df[player_df["season_name"].isin(seasons)]
        else:
            final_df = player_df

    # Replace empty values (= -1) with NULL values. Quicker for summing over columns.
    final_df = final_df.replace(-1, pd.NA)

    # Gather statistics for selected player.
    total_appearances = len(final_df)
    total_goals = final_df["goals"].sum(skipna=True)
    total_assists = final_df["assists"].sum(skipna=True)
    nationality = final_df["nationality"].mode().iat[0]
    total_yellows = final_df["yellow_cards"].sum(skipna=True)
    total_reds = final_df["red_cards"].sum(skipna=True)
    minutes_played = final_df["minutes_played"].sum(skipna=True)
    number_of_seasons = final_df["number_of_seasons"].mode().iat[0]

    # If main position/shirt number for a player is unavailable, use Unknown.
    main_position = (final_df.loc[final_df["player_position"] != "N/A", "player_position"].mode())
    main_position = main_position.iat[0] if not main_position.empty else "Unknown"
    shirt_number = (final_df.loc[final_df["shirt_number"].notna(), "shirt_number"].mode())
    shirt_number = shirt_number.iat[0] if not shirt_number.empty else "Unknown"

    # Find order for which a player played for a team
    team_order = final_df.groupby("team_name")["season_name"].min().reset_index()
    team_order["season_start"] = team_order["season_name"].str[:4].astype(int) # Order by season year.
    team_order = team_order.sort_values("season_start")
    teams = " – ".join(team_order["team_name"].tolist())

    # Player overview statistics.
    st.markdown(f"<h2 style='color:#FF800E;'>Player overview for {player.split(' (')[0]}:</h2>", unsafe_allow_html=True)
    st.markdown("<hr style='border: none; height: 2px; background-color: #FF800E;'>", unsafe_allow_html=True)

    # Seasons played in selected competition for player.
    st.metric("Number of seasons", number_of_seasons)

    # Appearances, goals and assists.
    col1, col2, col3 = st.columns(3)
    col1.metric("Appearances", total_appearances)
    col2.metric("Goals", total_goals)
    col3.metric("Assists (only tracked from 2015 onwards)", total_assists)

    # Nationality, most common position played and most used shirt number.
    col4, col5, col6 = st.columns(3)
    col4.metric("Nationality", nationality)
    col5.metric("Position", main_position)
    col6.metric("Most used shirt number", shirt_number)

    # Yellow cards, red cards and minutes played.
    col7, col8, col9 = st.columns(3)
    col7.metric("Yellow Cards", total_yellows)
    col8.metric("Red Cards", total_reds)
    col9.metric("Total minutes played", minutes_played)

    # Teams played for.
    st.markdown(
        f"""
        <div style='text-align: left; padding:10px; border-radius:10px;'>
            <p style='font-size:14px; color:white;'>Teams played for</p>
            <p style='font-size:18px;; margin:0;'>{teams}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Overview of appearances and goals per season.
    st.markdown(f"<h2 style='color:#FF800E;'>Appearances and goals per season for {player.split(' (')[0]}:</h2>", unsafe_allow_html=True)
    st.markdown("<hr style='border: none; height: 2px; background-color: #FF800E;'>", unsafe_allow_html=True)

    # Aggregate appearances and goals per season.
    season_stats = (
        final_df.groupby("season_name")
        .agg(Appearances=("player_name", "count"), Goals=("goals", "sum"))
        .reset_index()
    )

    # Sort by season.
    season_stats = season_stats.sort_values("season_name")

    # Extract numeric start year from season_name (e.g. "2015/2016" → 2015).
    season_stats["season_start"] = season_stats["season_name"].str[:4].astype(int)

    # Find first and last seasons that selected player played in.
    all_seasons = pd.DataFrame({
        "season_start": range(season_stats["season_start"].min(),
                              season_stats["season_start"].max() + 1)
    })

    # Merge with original dataframe to add seasons where a player didn't play between their first and last seasons.
    season_stats = all_seasons.merge(season_stats, on="season_start", how="left")

    # Rebuild proper season_name (e.g. 2015 -> 2015/2016).
    season_stats["Season"] = season_stats["season_start"].astype(str) + "/" + (season_stats["season_start"] + 1).astype(
        str)

    # Ensure appearances and goals where a player didn't play are set to 0.
    season_stats[["Appearances", "Goals"]] = season_stats[["Appearances", "Goals"]].fillna(0).astype(int)

    # Keep only the three columns from season_stats.
    season_stats = season_stats[["Season", "Appearances", "Goals"]]

    # Define appearances bar chart.
    bars = alt.Chart(season_stats).mark_bar(color="#FF800E").encode(
        x=alt.X("Season:N", title="Season"),
        y=alt.Y("Appearances:Q", axis=alt.Axis(title="Appearances", labels=False, ticks=False, grid=False,
                orient="left", titleColor="#FF800E")),
        tooltip=["Season", "Appearances", "Goals"]
    )

    # Define data labels for appearances.
    bar_labels = alt.Chart(season_stats).mark_text(
        align="center",
        baseline="bottom",
        dy=-2,  # Small offset above bar.
        color="#FF800E"
    ).encode(
        x="Season:N",
        y=alt.Y("Appearances:Q", axis=alt.Axis(title="Appearances", labels=False, ticks=False, grid=False,
                                               orient="left", titleColor="#FF800E")),
        text="Appearances:Q"
    )

    # Define goals line chart.
    line = alt.Chart(season_stats).mark_line(color="#1C9CE0", point=True).encode(
        x="Season:N",
        y=alt.Y("Goals:Q", axis=alt.Axis(title="Goals", labels=False, ticks=False, grid=False, orient="right",
                                         titleColor="#1C9CE0")),
        tooltip=["Season", "Goals"]
    )

    # Define data labels for goals.
    line_labels = alt.Chart(season_stats).mark_text(
        align="left",
        baseline="middle",
        dx=8,  # offset to the right of the point
        color="#1C9CE0"
    ).encode(
        x="Season:N",
        y=alt.Y("Goals:Q", axis=alt.Axis(title="Goals", labels=False, ticks=False, grid=False, orient="right",
                                         titleColor="#1C9CE0")),
        text="Goals:Q"
    )

    # Combine charts with dual axis.
    chart = alt.layer(bars, bar_labels, line, line_labels).resolve_scale(
        y="shared"  # Use the same scale for both y-axes.
    )

    st.altair_chart(chart, use_container_width=True)

create_streamlit_app()
