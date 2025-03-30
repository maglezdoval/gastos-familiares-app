import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import numpy as np
from sklearn.linear_model import LinearRegression
import sqlite3

# Configuración inicial de la aplicación
st.set_page_config(page_title="Gastos Familiares", layout="wide")
st.title("💸 Analizador de Gastos Familiares")

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

# Función para insertar un gasto en la base de datos
def insertar_gasto(fecha, categoria, subcategoria, comercio, concepto, importe, tipo, año, mes, dia):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO gastos (fecha, categoria, subcategoria, comercio, concepto, importe, tipo, año, mes, dia)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (fecha.strftime('%Y-%m-%d %H:%M:%S'), categoria, subcategoria, comercio, concepto, importe, tipo, año, mes, dia))
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Error al insertar gasto en la base de datos: {e}")
    finally:
        conn.close()

# Función para obtener gastos desde la base de datos
def obtener_gastos():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM gastos')
    gastos = cursor.fetchall()
    conn.close()
    return gastos

seccion = st.sidebar.radio("Ir a sección:", ["🏠 Inicio", "📊 Análisis", "📈 Evolución", "✍️ Clasificación", "⚙️ Configuración"])

# ⚙️ CONFIGURACIÓN (accesible siempre)
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

    archivo_config = st.file_uploader("📤 Importar configuración (CSV)", type="csv", key="config_upload")
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

# 📁 CARGA DE ARCHIVO
uploaded_file = st.file_uploader("📁 Sube tu archivo CSV", type="csv")

if not uploaded_file:
    st.warning("👆 Sube un archivo CSV para acceder al resto de secciones")
    st.stop()

# PROCESAMIENTO
try:
    try:
        df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')
    except pd.errors.ParserError as e:
        st.error(f"❌ Error de parseo del archivo: {e}")
        st.stop()
    except UnicodeDecodeError as e:
        st.error(f"❌ Error de codificación del archivo: {e}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error inesperado: {e}")
        st.stop()
except Exception as e:
    st.error(f"❌ Error al leer el archivo: {e}")
    st.stop()

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

columnas_esperadas = {"CONCEPTO", "COMERCIO", "CATEGORÍA", "SUBCATEGORÍA", "IMPORTE", "TIPO", "AÑO", "MES", "DIA"}
columnas_no_mapeadas = [col for col in df.columns if col not in renombrar_columnas.values() and col not in columnas_esperadas]
if columnas_no_mapeadas:
    st.warning(f"⚠️ Columnas no reconocidas tras el renombrado: {columnas_no_mapeadas}")

if not columnas_esperadas.issubset(df.columns):
    faltantes = columnas_esperadas - set(df.columns)
    st.error(f"❌ Faltan columnas: {faltantes}")
    st.stop()

df['TIPO'] = df['TIPO'].astype(str).str.strip().str.upper()
df = df[df['TIPO'] == 'GASTO']
df['IMPORTE'] = df['IMPORTE'].astype(str).str.replace(',', '.').astype(float)
df[['AÑO', 'MES', 'DIA']] = df[['AÑO', 'MES', 'DIA']].apply(pd.to_numeric, errors='coerce')

# Corrección: Creando la fecha correctamente
df['FECHA'] = pd.to_datetime(
    {
        'year': df['AÑO'], 
        'month': df['MES'], 
        'day': df['DIA']
    }, 
    errors='coerce'
)

if df['FECHA'].isna().sum() > 0:
    st.warning("⚠️ Algunas fechas no se pudieron convertir correctamente.")

# Insertar datos del DataFrame en la base de datos
for i, row in df.iterrows():
    insertar_gasto(
        fecha=row['FECHA'],
        categoria=row['CATEGORÍA'],
        subcategoria=row.get('SUBCATEGORÍA', ''),
        comercio=row.get('COMERCIO', ''),
        concepto=row.get('CONCEPTO', ''),
        importe=row['IMPORTE'],
        tipo=row['TIPO'],
        año=row['AÑO'],
        mes=row['MES'],
        dia=row['DIA']
    )

# Obtener datos de la base de datos
gastos = obtener_gastos()
df = pd.DataFrame(gastos, columns=['id', 'fecha', 'categoria', 'subcategoria', 'comercio', 'concepto', 'importe', 'tipo', 'año', 'mes', 'dia'])

# 🏠 INICIO
if seccion == "🏠 Inicio":
    st.header("📋 Tabla de Transacciones")
    st.dataframe(df, use_container_width=True)

# 📊 ANÁLISIS
elif seccion == "📊 Análisis":
    st.header("📊 Análisis e Insights")
    periodo = st.selectbox("Selecciona un periodo:", ["Último mes", "Últimos 3 meses", "Último año", "Todo el histórico"])
    hoy = datetime.now()
    if periodo == "Último mes":
        fecha_inicio = hoy - timedelta(days=30)
    elif periodo == "Últimos 3 meses":
        fecha_inicio = hoy - timedelta(days=90)
    elif periodo == "Último año":
        fecha_inicio = hoy - timedelta(days=365)
    else:
        fecha_inicio = df['fecha'].min()

    df['fecha'] = pd.to_datetime(df['fecha'])
    df_periodo = df[df['fecha'] >= fecha_inicio]
    
    # Verificar que hay datos para el período seleccionado
    if df_periodo.empty:
        st.warning("No hay datos para el período seleccionado.")
    else:
        top_comercios = df_periodo.groupby("comercio")["importe"].sum().sort_values(ascending=False).head(5)
        st.subheader("🏪 Top 5 Comercios con más gasto")
        st.bar_chart(top_comercios)

        resumen = df_periodo.groupby(["año", "mes"])["importe"].sum().reset_index()
        resumen['TOTAL'] = resumen['importe'].map(lambda x: f"{x:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'))
        st.subheader("📅 Resumen por Año y Mes")
        st.dataframe(resumen, use_container_width=True)

        mes_actual = hoy.month
        anio_actual = hoy.year
        actual = df_periodo[(df_periodo['año'] == anio_actual) & (df_periodo['mes'] == mes_actual)]
        if not actual.empty:
            mayor_gasto = actual.loc[actual['importe'].idxmax()]
            st.info(f"💥 Mayor gasto este mes: {mayor_gasto['importe']:,.2f} € en '{mayor_gasto['comercio']}'".replace(',', 'X').replace('.', ',').replace('X', '.'))
            mes_anterior = mes_actual - 1 if mes_actual > 1 else 12
            anio_anterior = anio_actual if mes_actual > 1 else anio_actual - 1
            anterior = df_periodo[(df_periodo['año'] == anio_anterior) & (df_periodo['mes'] == mes_anterior)]
            total_actual = actual['importe'].sum()
            total_anterior = anterior['importe'].sum() if not anterior.empty else 0
            diferencia = total_actual - total_anterior
            st.info(f"📈 Has gastado {diferencia:+,.2f} € {'más' if diferencia > 0 else 'menos'} que el mes pasado".replace(',', 'X').replace('.', ',').replace('X', '.'))

# 📈 EVOLUCIÓN
elif seccion == "📈 Evolución":
    st.header("📈 Evolución mensual de gastos")
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
            df_merged = pd.merge(df_base, mensual_actual, on="MES", how="left").fillna(0)

            hoy = datetime.now()
            mostrar_prediccion = año_seleccionado == hoy.year
            if mostrar_prediccion:
                df_historico = df[df['año'] < año_seleccionado].copy()
                if not df_historico.empty:
                    df_hist_group = df_historico.groupby(['año', 'mes'])['importe'].sum().reset_index()
                    df_hist_group['mes'] = df_hist_group['mes'].astype(int)
                    X = df_hist_group['mes'].values.reshape(-1, 1)
                    y = df_hist_group['importe'].values
                    modelo = LinearRegression().fit(X, y)
                    pred = modelo.predict(np.array(meses).reshape(-1, 1))
                    df_merged['PREDICCION'] = pred

            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(df_merged['MES'], df_merged['importe'], marker='o', label="Real", linewidth=2)
            if mostrar_prediccion and 'PREDICCION' in df_merged.columns:
                ax.plot(df_merged['MES'], df_merged['PREDICCION'], linestyle='--', marker='x', color='gray', label="Predicción")
            ax.set_xticks(meses)
            ax.set_title(f"Evolución mensual de gastos - {año_seleccionado}")
            ax.set_xlabel("Mes")
            ax.set_ylabel("Importe (€)")
            ax.legend()
            plt.grid(True, linestyle='--', alpha=0.3)
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

        # Asegurar que siempre hay al menos una opción en las listas
        if not comercios:
            comercios = [""]
        if not categorias:
            categorias = [""]
        if not subcategorias:
            subcategorias = [""]

        for i, row in df_edit.iterrows():
            with st.expander(f"🧾 {row['concepto']} - {row['importe']} €"):
                comercio_actual = row['comercio'] if isinstance(row['comercio'], str) else ""
                categoria_actual = row['categoria'] if isinstance(row['categoria'], str) else ""
                subcategoria_actual = row['subcategoria'] if isinstance(row['subcategoria'], str) else ""

                comercio_index = comercios.index(comercio_actual) if comercio_actual in comercios else 0
                categoria_index = categorias.index(categoria_actual) if categoria_actual in categorias else 0
                subcategoria_index = subcategorias.index(subcategoria_actual) if subcategoria_actual in subcategorias else 0

                comercio_nuevo = st.selectbox("Comercio", options=comercios, index=comercio_index, key=f"comercio_{i}")
                categoria_nueva = st.selectbox("Categoría", options=categorias, index=categoria_index, key=f"categoria_{i}")
                subcat_nueva = st.selectbox("Subcategoría", options=subcategorias, index=subcategoria_index, key=f"subcat_{i}")

                df.at[i, 'comercio'] = comercio_nuevo
                df.at[i, 'categoria'] = categoria_nueva
                df.at[i, 'subcategoria'] = subcat_nueva

        st.download_button("💾 Descargar CSV actualizado", df.to_csv(index=False), file_name="gastos_actualizados.csv", mime="text/csv")

# Cerrar la conexión a la base de datos
conn.close()
