"""
INSTRUÇÕES PARA DEPLOY NO STREAMLIT COMMUNITY CLOUD (Menos de 2 minutos):

1. Crie uma conta no GitHub (https://github.com) se não tiver uma.
2. Crie um novo repositório público.
3. Faça o upload de dois arquivos para este repositório:
   - Este arquivo (app.py)
   - O arquivo requirements.txt
4. Acesse o Streamlit Community Cloud (https://share.streamlit.io) e faça login com seu GitHub.
5. Clique em "New app" (Novo aplicativo).
6. Selecione o repositório que você acabou de criar, a branch (geralmente 'main') e o arquivo principal ('app.py').
7. Clique em "Deploy!". Em cerca de um a dois minutos, seu aplicativo estará online e acessível por um link público.
"""

import streamlit as st
import pandas as pd
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium
from shapely.geometry import Point, Polygon
import datetime

st.set_page_config(page_title="Rastreamento Logístico", layout="wide")

st.title("🚚 Dashboard de Rastreamento Logístico e Geofencing")

# 1. Upload do Arquivo
uploaded_file = st.file_uploader("Faça o upload do arquivo Excel com os dados de rastreamento", type=["xlsx", "xls"])

if uploaded_file:
    try:
        # Lendo o arquivo
        df = pd.read_excel(uploaded_file)

        # Verificando colunas obrigatórias
        required_columns = ['ID_Veiculo', 'Timestamp', 'Latitude', 'Longitude']
        if not all(col in df.columns for col in required_columns):
            st.error(f"Erro: O arquivo deve conter as seguintes colunas: {', '.join(required_columns)}")
            st.stop()

        # Convertendo Timestamp para datetime
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])

        # 2. Lógica de Filtro 30min
        min_time = df['Timestamp'].min().replace(second=0, microsecond=0)
        max_time = df['Timestamp'].max().replace(second=0, microsecond=0)

        # Criando opções de 30 em 30 minutos
        time_options = []
        current_time = min_time
        while current_time <= max_time + datetime.timedelta(minutes=30):
            time_options.append(current_time)
            current_time += datetime.timedelta(minutes=30)

        selected_time = st.select_slider(
            "Selecione o horário (Filtro de 30 min - Last Known Position):",
            options=time_options,
            format_func=lambda x: x.strftime("%d/%m/%Y %H:%M")
        )

        # Filtrando: Para cada veículo, pegar o registro mais recente <= selected_time
        df_filtered = df[df['Timestamp'] <= selected_time]
        if df_filtered.empty:
            st.warning("Nenhum dado disponível para o horário selecionado ou anterior a ele.")
            st.stop()

        # Last Known Position
        last_positions = df_filtered.sort_values('Timestamp').groupby('ID_Veiculo').tail(1)

        # 3. Mapa de Geofencing
        st.subheader("Mapa de Rastreamento e Geofencing")

        # Centro do mapa
        center_lat = last_positions['Latitude'].mean()
        center_lon = last_positions['Longitude'].mean()
        m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

        # Adicionando marcadores dos caminhões
        for _, row in last_positions.iterrows():
            folium.Marker(
                location=[row['Latitude'], row['Longitude']],
                popup=f"Veículo: {row['ID_Veiculo']}<br>Hora: {row['Timestamp'].strftime('%H:%M:%S')}",
                icon=folium.Icon(color="blue", icon="truck", prefix='fa')
            ).add_to(m)

        # Adicionando ferramenta de desenho
        draw = Draw(
            draw_options={
                'polyline': False,
                'rectangle': True,
                'polygon': True,
                'circle': False,
                'marker': False,
                'circlemarker': False
            },
            edit_options={'edit': False}
        )
        m.add_child(draw)

        # Renderizando o mapa e capturando os desenhos
        map_data = st_folium(m, width="100%", height=500)

        # 4. Cálculo de Ocupação
        drawn_polygons = []
        if map_data and map_data.get("all_drawings"):
            for drawing in map_data["all_drawings"]:
                if drawing["geometry"]["type"] in ["Polygon", "Rectangle"]:
                    coords = drawing["geometry"]["coordinates"][0]
                    drawn_polygons.append(Polygon(coords))

        trucks_in_geofence = 0
        if drawn_polygons:
            for _, row in last_positions.iterrows():
                point = Point(row['Longitude'], row['Latitude']) # Shapely usa (lon, lat)
                for poly in drawn_polygons:
                    if poly.contains(point):
                        trucks_in_geofence += 1
                        break

        # Exibindo contador destacado
        st.markdown("---")
        st.metric(label="🚛 Caminhões dentro das áreas demarcadas (Geofences)", value=trucks_in_geofence)

        st.dataframe(last_positions[['ID_Veiculo', 'Timestamp', 'Latitude', 'Longitude']].reset_index(drop=True))

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
else:
    st.info("Aguardando o upload do arquivo Excel para iniciar.")
