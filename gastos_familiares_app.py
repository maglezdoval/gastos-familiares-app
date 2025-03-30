import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import numpy as np
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="Gastos Familiares", layout="wide")
st.title("💸 Analizador de Gastos Familiares")

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

    st.session_state["COMERCIOS"] = editar_lista("COMERCIO", st.session_state.get("COMERCIOS", []))
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
    df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8', errors='ignore')
except Exception as e:
    st.error(f"❌ Error al leer el archivo: {e}")
    st.stop()

renombrar_columnas = {
    "subcategoria": "SUBCATEGORÍA",
    "subcategoría": "SUBCATEGORÍA",
    "concepto": "CONCEPTO",
    "comercio": "COMERCIO",
    "categoría": "CATEGORÍA",
    "categoria": "CATEGORÍA"
}}
df.columns = [renombrar_columnas.get(col.lower().strip(), col.upper().strip()) for col in df.columns]

columnas_esperadas = {"CONCEPTO", "COMERCIO", "CATEGORÍA", "SUBCATEGORÍA", "IMPORTE", "TIPO", "AÑO", "MES", "DIA"}
if not columnas_esperadas.issubset(df.columns):
    faltantes = columnas_esperadas - set(df.columns)
    st.error(f"❌ Faltan columnas: {faltantes}")
    st.stop()

df['TIPO'] = df['TIPO'].astype(str).str.strip().str.upper()
df = df[df['TIPO'] == 'GASTO']
df['IMPORTE'] = df['IMPORTE'].astype(str).str.replace(',', '.').astype(float)
df[['AÑO', 'MES', 'DIA']] = df[['AÑO', 'MES', 'DIA']].apply(pd.to_numeric, errors='coerce')
df['FECHA'] = pd.to_datetime(df[['AÑO', 'MES', 'DIA']], errors='coerce')

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
        fecha_inicio = df['FECHA'].min()

    df_periodo = df[df['FECHA'] >= fecha_inicio]
    top_comercios = df_periodo.groupby("COMERCIO")["IMPORTE"].sum().sort_values(ascending=False).head(5)
    st.subheader("🏪 Top 5 Comercios con más gasto")
    st.bar_chart(top_comercios)

    resumen = df_periodo.groupby(["AÑO", "MES"])["IMPORTE"].sum().reset_index()
    resumen['TOTAL'] = resumen['IMPORTE'].map(lambda x: f"{x:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'))
    st.subheader("📅 Resumen por Año y Mes")
    st.dataframe(resumen, use_container_width=True)

    mes_actual = hoy.month
    anio_actual = hoy.year
    actual = df_periodo[(df_periodo['AÑO'] == anio_actual) & (df_periodo['MES'] == mes_actual)]
    if not actual.empty:
        mayor_gasto = actual.loc[actual['IMPORTE'].idxmax()]
        st.info(f"💥 Mayor gasto este mes: {mayor_gasto['IMPORTE']:,.2f} € en '{mayor_gasto['COMERCIO']}'".replace(',', 'X').replace('.', ',').replace('X', '.'))
        mes_anterior = mes_actual - 1 if mes_actual > 1 else 12
        anio_anterior = anio_actual if mes_actual > 1 else anio_actual - 1
        anterior = df_periodo[(df_periodo['AÑO'] == anio_anterior) & (df_periodo['MES'] == mes_anterior)]
        total_actual = actual['IMPORTE'].sum()
        total_anterior = anterior['IMPORTE'].sum() if not anterior.empty else 0
        diferencia = total_actual - total_anterior
        st.info(f"📈 Has gastado {diferencia:+,.2f} € {'más' if diferencia > 0 else 'menos'} que el mes pasado".replace(',', 'X').replace('.', ',').replace('X', '.'))

# 📈 EVOLUCIÓN
elif seccion == "📈 Evolución":
    st.header("📈 Evolución mensual de gastos")
    años_disponibles = sorted(df['AÑO'].dropna().unique())
    año_seleccionado = st.selectbox("Seleccionar año para la gráfica", años_disponibles, index=len(años_disponibles)-1)
    meses = list(range(1, 13))
    df_base = pd.DataFrame({"MES": meses})
    df_actual = df[df['AÑO'] == año_seleccionado].copy()
    mensual_actual = df_actual.groupby('MES')['IMPORTE'].sum().reset_index()
    df_merged = pd.merge(df_base, mensual_actual, on="MES", how="left").fillna(0)

    mostrar_prediccion = año_seleccionado == hoy.year
    if mostrar_prediccion:
        df_historico = df[df['AÑO'] < año_seleccionado].copy()
        if not df_historico.empty:
            df_hist_group = df_historico.groupby(['AÑO', 'MES'])['IMPORTE'].sum().reset_index()
            df_hist_group['MES'] = df_hist_group['MES'].astype(int)
            X = df_hist_group['MES'].values.reshape(-1, 1)
            y = df_hist_group['IMPORTE'].values
            modelo = LinearRegression().fit(X, y)
            pred = modelo.predict(np.array(meses).reshape(-1, 1))
            df_merged['PREDICCION'] = pred

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df_merged['MES'], df_merged['IMPORTE'], marker='o', label="Real", linewidth=2)
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
        df_edit = df_edit[df_edit['CATEGORÍA'].isna() | (df_edit['CATEGORÍA'].astype(str).str.strip() == '')]

    comercios = st.session_state.get("COMERCIOS", sorted(df['COMERCIO'].dropna().unique().tolist()))
    categorias = st.session_state.get("CATEGORIAS", sorted(df['CATEGORÍA'].dropna().unique().tolist()))
    subcategorias = st.session_state.get("SUBCATEGORIAS", sorted(df['SUBCATEGORÍA'].dropna().unique().tolist()))

    for i, row in df_edit.iterrows():
        with st.expander(f"🧾 {row['CONCEPTO']} - {row['IMPORTE']} €"):
            comercio_nuevo = st.selectbox("Comercio", options=comercios, index=comercios.index(row['COMERCIO']) if row['COMERCIO'] in comercios else 0, key=f"comercio_{i}")
            categoria_nueva = st.selectbox("Categoría", options=categorias, index=categorias.index(row['CATEGORÍA']) if row['CATEGORÍA'] in categorias else 0, key=f"categoria_{i}")
            subcat_nueva = st.selectbox("Subcategoría", options=subcategorias, index=subcategorias.index(row['SUBCATEGORÍA']) if row['SUBCATEGORÍA'] in subcategorias else 0, key=f"subcat_{i}")
            df.at[i, 'COMERCIO'] = comercio_nuevo
            df.at[i, 'CATEGORÍA'] = categoria_nueva
            df.at[i, 'SUBCATEGORÍA'] = subcat_nueva

    st.download_button("💾 Descargar CSV actualizado", df.to_csv(index=False), file_name="gastos_actualizados.csv", mime="text/csv")
