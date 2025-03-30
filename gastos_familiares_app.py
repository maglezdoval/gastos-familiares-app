import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import numpy as np
from sklearn.linear_model import LinearRegression
import sqlite3
from sqlalchemy import create_engine

# Configuración inicial de la aplicación
st.set_page_config(page_title="Gastos Familiares", layout="wide")
st.title(" Analizador de Gastos Familiares")

# Conectar a la base de datos (o crearla si no existe)
def get_db_connection():
    conn = sqlite3.connect('gastos.db')
    conn.row_factory = sqlite3.Row
    return conn

# Crear una tabla para los gastos si no existe
def create_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            categoria TEXT NOT NULL,
            subcategoria TEXT,
            comercio TEXT,
            concepto TEXT,
            importe REAL NOT NULL,
            tipo TEXT NOT NULL,
            año INTEGER NOT NULL,
            mes INTEGER NOT NULL,
            dia INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

create_table()

# Función para obtener gastos desde la base de datos
def obtener_gastos():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM gastos')
    gastos = cursor.fetchall()
    conn.close()
    return gastos

seccion = st.sidebar.radio("Ir a sección:", [" Inicio", " Análisis", " Evolución", "✍️ Clasificación", "⚙️ Configuración"])

# ⚙️ CONFIGURACIÓN
if seccion == "⚙️ Configuración":
    st.header("⚙️ Administración de categorías y comercios")

    def editar_lista(nombre, valores_iniciales):
        st.subheader(nombre)
        valor_inicial = "\n".join(valores_iniciales) if valores_iniciales else ""
        texto = st.text_area(f"Ingresar valores para {nombre} (uno por línea):", value=valor_inicial) or ""
        lista = [v.strip() for v in texto.splitlines() if v.strip()]
        return sorted(set(lista))

    for clave in ["COMERCIOS", "CATEGORIAS", "SUBCATEGORIAS"]:
        if clave not in st.session_state:
            st.session_state[clave] = []

    st.session_state["COMERCIOS"] = editar_lista("COMERCIO", st.session_state["COMERCIOS"])
    st.session_state["CATEGORIAS"] = editar_lista("CATEGORÍA", st.session_state.get("CATEGORIAS", []))
    st.session_state["SUBCATEGORIAS"] = editar_lista("SUBCATEGORÍA", st.session_state.get("SUBCATEGORIAS", []))

    st.download_button("⬇️ Descargar configuración", data=pd.DataFrame({
        'COMERCIO': st.session_state['COMERCIOS'],
        'CATEGORÍA': st.session_state['CATEGORIAS'],
        'SUBCATEGORÍA': st.session_state['SUBCATEGORIAS']
    }).to_csv(index=False), file_name="configuracion_gastos.csv", mime="text/csv")

    archivo_config = st.file_uploader(" Importar configuración (CSV)", type="csv", key="config_upload")
    if archivo_config:
        config_df = pd.read_csv(archivo_config)
        if 'COMERCIO' in config_df.columns:
            st.session_state['COMERCIOS'] = sorted(config_df['COMERCIO'].dropna().unique().tolist())
        if 'CATEGORÍA' in config_df.columns:
            st.session_state['CATEGORIAS'] = sorted(config_df['CATEGORÍA'].dropna().unique().tolist())
        if 'SUBCATEGORÍA' in config_df.columns:
            st.session_state['SUBCATEGORIAS'] = sorted(config_df['SUBCATEGORÍA'].dropna().unique().tolist())
        st.success("✅ Configuración importada correctamente")

    st.stop()

# CARGA DE ARCHIVO
uploaded_file = st.file_uploader(" Sube tu archivo CSV", type="csv")
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')

        # Validación de columnas
        columnas_esperadas = {"CONCEPTO", "COMERCIO", "CATEGORÍA", "IMPORTE", "TIPO", "AÑO", "MES", "DIA"} #subcategoria eliminada.
        if not columnas_esperadas.issubset(df.columns):
            faltantes = columnas_esperadas - set(df.columns)
            st.error(f"❌ Faltan columnas: {faltantes}")
            st.stop()
        #validación de tipos de datos.
        df['IMPORTE'] = pd.to_numeric(df['IMPORTE'], errors='coerce')
        df[['AÑO', 'MES', 'DIA']] = df[['AÑO', 'MES', 'DIA']].apply(pd.to_numeric, errors='coerce')
        df = df.dropna(subset=['IMPORTE','AÑO','MES','DIA'])
        #Se añade subcategoria si no existe.
        if 'SUBCATEGORÍA' not in df.columns:
            df['SUBCATEGORÍA'] = ""

        # RENOMBRAR COLUMNAS
        renombrar_columnas = {
            "subcategoria": "SUBCATEGORÍA",
            "subcategoría": "SUBCATEGORÍA",
            "concepto": "CONCEPTO",
            "comercio": "COMERCIO",
            "categoría": "CATEGORÍA",
            "categoria": "CATEGORÍA",
            "cuenta": "CUENTA"
        }

        df.columns = [renombrar_columnas.get(col.lower().strip(), col.upper().strip()) for col in df.columns]

        columnas_no_mapeadas = [col for col in df.columns if col not in renombrar_columnas.values() and col not in columnas_esperadas]
        if columnas_no_mapeadas:
            st.warning(f"⚠️ Columnas no reconocidas tras el renombrado: {columnas_no_mapeadas}")

        # LIMPIEZA Y FORMATEO

        df['TIPO'] = df['TIPO'].astype(str).str.strip().str.upper()
        df = df[df['TIPO'] == 'GASTO']
        df['IMPORTE'] = df['IMPORTE'].astype(str).str.replace(',', '.').astype(float)
        df['FECHA'] = pd.to_datetime({'year': df['AÑO'], 'month': df['MES'], 'day': df['DIA']}, errors='coerce')
        df['FECHA'] = df['FECHA'].dt.strftime('%Y-%m-%d %H:%M:%S')

        if df['FECHA'].isna().sum() > 0:
            st.warning("⚠️ Algunas fechas no se pudieron convertir correctamente.")

        # INSERCIÓN EN BASE DE DATOS
        with st.spinner("Insertando datos en la base de datos..."):
            try:
                engine = create_engine('sqlite:///gastos.db')
                #Modificacion aqui.
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(gastos)")
                columns = [column[1] for column in cursor.fetchall()]
                if "SUBCATEGORÍA" not in columns:
                    df.to_sql('gastos', engine, if_exists='append', index=False)
                else:
                    df.to_sql('gastos', engine, if_exists='append', index=False)
                st.success("✅ Datos insertados correctamente.")
            except Exception as e:
                st.error(f"❌ Error al insertar datos en la base de datos: {e}")

        # OBTENER DATOS
        registros = obtener_gastos()
        df = pd.DataFrame(registros, columns=['id', 'fecha', 'categoria', 'subcategoria', 'comercio', 'concepto', 'importe', 'tipo', 'año', 'mes', 'dia'])

        #  INICIO
        if seccion == " Inicio":
            st.header(" Tabla de Transacciones")
            st.dataframe(df, use_container_width=True)

        #  ANÁLISIS
        elif seccion == " Análisis":
            st.header(" Análisis e Insights")
            periodo = st.selectbox("Selecciona un periodo:", ["Último mes", "Últimos 3 meses", "Último año", "Todo el histórico"])
            hoy = datetime.now()
            if periodo == "Último mes":
                fecha_inicio = hoy - timedelta(days=30)
            elif periodo == "Últimos 3 meses":
                fecha_inicio = hoy - timedelta(days=90)
            elif periodo == "Último año":
                fecha_inicio = hoy - timedelta(days=365)
            else:
                fecha_inicio = pd.to_datetime(df['fecha']).min()

            df['fecha'] = pd.to_datetime(df['fecha'])
            df_periodo = df[df['fecha'] >= fecha_inicio]

            if df_periodo.empty:
                st.warning("No hay datos para el período seleccionado.")
            else:
                top_comercios = df_periodo.groupby("comercio")['importe'].sum().sort_values(ascending=False).head(5)
                st.subheader(" Top 5 Comercios con más gasto")
                st.bar_chart(top_comercios)

                resumen = df_periodo.groupby(["año", "mes"])['importe'].sum().reset_index()
                resumen['TOTAL'] = resumen['importe'].map(lambda x: f"{x:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'))
                st.subheader(" Resumen por Año y Mes")
                st.dataframe(resumen, use_container_width=True)

                actual = df_periodo[(df_periodo['año'] == hoy.year) & (df_periodo['mes'] == hoy.month)]
                if not actual.empty:
                    mayor_gasto = actual.loc[actual['importe'].idxmax()]
                    st.info(f" Mayor gasto este mes: {mayor_gasto['importe']:,.2f} € en '{mayor_gasto['comercio']}'".replace(',', 'X').replace('.', ',').replace('X', '.'))
                    mes_anterior = hoy.month - 1 if hoy.month > 1 else 12
                    año_anterior = hoy.year if hoy.month > 1 else hoy.year - 1
                    anterior = df_periodo[(df_periodo['año'] == año_anterior) & (df_periodo['mes'] == mes_anterior)]
                    total_actual = actual['importe'].sum()
                    total_anterior = anterior['importe'].sum() if not anterior.empty else 0
                    diferencia = total_actual - total_anterior
                    st.info(f" Has gastado {diferencia:+,.2f} € {'más' if diferencia > 0 else 'menos'} que el mes pasado".replace(',', 'X').replace('.', ',').replace('X', '.'))

        #  EVOLUCIÓN
        elif seccion == " Evolución":
            st.header(" Evolución mensual de gastos")
            años_disponibles = sorted(df['año'].dropna().unique())

            if not años_disponibles:
                st.warning("No hay datos de años disponibles.")
            else:
                año_seleccionado = st.selectbox("Seleccionar año para la gráfica", años_disponibles, index=len(años_disponibles)-1)
                meses = list(range(1, 13))
                df_base = pd.DataFrame({"MES": meses})
                df_actual = df[df['año'] == año_seleccionado].copy()

                if df_actual.empty:
                    st.warning(f"No hay datos para el año {año_seleccionado}.")
                else:
                    mensual_actual = df_actual.groupby('mes')['importe'].sum().reset_index()
                    mensual_actual.rename(columns={'mes': 'MES'}, inplace=True)
                    df_merged = pd.merge(df_base, mensual_actual, on="MES", how="left").fillna(0)

                hoy = datetime.now()
                mostrar_prediccion = año_seleccionado == hoy.year
                if mostrar_prediccion:
                    df_historico = df[df['año'] < año_seleccionado].copy()
                    if not df_historico.empty:
                        df_hist_group = df_historico.groupby(['año', 'mes'])['importe'].sum().reset_index()
                        X = df_hist_group['mes'].values.reshape(-1, 1)
                        y = df_hist_group['importe'].values
                        modelo = LinearRegression().fit(X, y)
                        pred = modelo.predict(np.array(meses).reshape(-1, 1))
                        df_merged['PREDICCION'] = pred

                fig, ax = plt.subplots(figsize=(10, 5))
                ax.plot(df_merged['MES'], df_merged['importe'], marker='o', label="Real", linewidth=2)
                if mostrar_prediccion and 'PREDICCION' in df_merged.columns:
                    ax.plot(df_merged['MES'], df_merged['PREDICCION'], linestyle='--', marker='x', label="Predicción")
                ax.set_xticks(meses)
                ax.set_title(f"Evolución mensual de gastos - {año_seleccionado}")
                ax.set_xlabel("Mes")
                ax.set_ylabel("Importe (€)")
                ax.legend()
                ax.grid(True, linestyle='--', alpha=0.3)
                st.pyplot(fig)

        # ✍️ CLASIFICACIÓN
        elif seccion == "✍️ Clasificación":
            st.header("✍️ Clasificación y edición de transacciones")
            solo_vacias = st.checkbox("Mostrar solo sin categorizar")
            df_edit = df.copy()
            if solo_vacias:
                df_edit = df_edit[df_edit['categoria'].isna() | (df_edit['categoria'].astype(str).str.strip() == '')]

            if df_edit.empty:
                st.info("No hay transacciones para mostrar con los filtros actuales.")
            else:
                comercios = st.session_state.get("COMERCIOS", sorted(df['comercio'].dropna().unique().tolist()))
                categorias = st.session_state.get("CATEGORIAS", sorted(df['categoria'].dropna().unique().tolist()))
                subcategorias = st.session_state.get("SUBCATEGORIAS", sorted(df['subcategoria'].dropna().unique().tolist()))

                if not comercios:
                    comercios = [""]
                if not categorias:
                    categorias = [""]
                if not subcategorias:
                    subcategorias = [""]

                for i, row in df_edit.iterrows():
                    with st.expander(f" {row['concepto']} - {row['importe']} €"):
                        comercio_nuevo = st.selectbox("Comercio", options=comercios, index=comercios.index(row['comercio']) if row['comercio'] in comercios else 0, key=f"comercio_{i}")
                        categoria_nueva = st.selectbox("Categoría", options=categorias, index=categorias.index(row['categoria']) if row['categoria'] in categorias else 0, key=f"categoria_{i}")
                        subcat_nueva = st.selectbox("Subcategoría", options=subcategorias, index=subcategorias.index(row['subcategoria']) if row['subcategoria'] in subcategorias else 0, key=f"subcat_{i}")

                        df.at[i, 'comercio'] = comercio_nuevo
                        df.at[i, 'categoria'] = categoria_nueva
                        df.at[i, 'subcategoria'] = subcat_nueva

                st.download_button(" Descargar CSV actualizado", df.to_csv(index=False), file_name="gastos_actualizados.csv", mime="text/csv")
    except Exception as e:
        st.error(f"❌ Error al leer el archivo: {e}")
