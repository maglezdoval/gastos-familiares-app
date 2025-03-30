import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="Gastos Familiares", layout="wide")
st.title("💸 Analizador de Gastos Familiares")

# Función segura para construir fechas
def construir_fecha_segura(row):
    try:
        return datetime(int(row['AÑO']), int(row['MES']), int(row['DIA']))
    except:
        return pd.NaT

# Subida de archivo CSV
uploaded_file = st.file_uploader("📁 Sube tu archivo CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')
    df['TIPO'] = df['TIPO'].astype(str).str.strip().str.upper()
    df = df[df['TIPO'] == 'GASTO']

    renombrar_columnas = {
        "subcategoria": "SUBCATEGORÍA",
        "subcategoría": "SUBCATEGORÍA",
        "concepto": "CONCEPTO",
        "comercio": "COMERCIO",
        "categoría": "CATEGORÍA",
        "categoria": "CATEGORÍA"
    }
    df.columns = [renombrar_columnas.get(col.lower().strip(), col.upper().strip()) for col in df.columns]

    columnas_esperadas = {"CONCEPTO", "COMERCIO", "CATEGORÍA", "SUBCATEGORÍA", "IMPORTE", "AÑO", "MES", "DIA"}
    if not columnas_esperadas.issubset(df.columns):
        st.error(f"❌ Columnas encontradas: {df.columns.tolist()}\n✅ Se esperaban: {list(columnas_esperadas)}")
    else:
        df['IMPORTE'] = df['IMPORTE'].astype(str).str.replace(',', '.').astype(float)
        df[['AÑO', 'MES', 'DIA']] = df[['AÑO', 'MES', 'DIA']].apply(pd.to_numeric, errors='coerce')
        df['FECHA'] = df.apply(construir_fecha_segura, axis=1)

        st.success("✅ CSV cargado correctamente")

        st.sidebar.header("🔎 Filtros")
        concepto = st.sidebar.text_input("Filtrar por CONCEPTO")

        comercio = st.sidebar.selectbox("Filtrar por COMERCIO", ["Todos"] + sorted(df['COMERCIO'].dropna().unique().tolist()))
        categoria = st.sidebar.selectbox("Filtrar por CATEGORÍA", ["Todos"] + sorted(df['CATEGORÍA'].dropna().unique().tolist()))
        subcategoria = st.sidebar.selectbox("Filtrar por SUBCATEGORÍA", ["Todos"] + sorted(df['SUBCATEGORÍA'].dropna().unique().tolist()))

        cuenta = st.sidebar.selectbox("Filtrar por CUENTA", ["Todos"] + sorted(df['CUENTA'].dropna().unique().tolist()) if 'CUENTA' in df.columns else ["Todos"])

        fecha_min = df['FECHA'].min()
        fecha_max = df['FECHA'].max()
        fecha_inicio, fecha_fin = st.sidebar.date_input("Filtrar por rango de fechas", [fecha_min, fecha_max])

        importe_min = float(df['IMPORTE'].min())
        importe_max = float(df['IMPORTE'].max())
        min_val, max_val = st.sidebar.slider("Filtrar por IMPORTE", min_value=importe_min, max_value=importe_max, value=(importe_min, importe_max))

        df_filtrado = df.copy()

        if concepto:
            df_filtrado = df_filtrado[df_filtrado["CONCEPTO"].str.contains(concepto, case=False, na=False)]
        if comercio != "Todos":
            df_filtrado = df_filtrado[df_filtrado["COMERCIO"] == comercio]
        if categoria != "Todos":
            df_filtrado = df_filtrado[df_filtrado["CATEGORÍA"] == categoria]
        if subcategoria != "Todos":
            df_filtrado = df_filtrado[df_filtrado["SUBCATEGORÍA"] == subcategoria]
        if cuenta != "Todos" and 'CUENTA' in df.columns:
            df_filtrado = df_filtrado[df_filtrado["CUENTA"] == cuenta]

        df_filtrado = df_filtrado[
            (df_filtrado["FECHA"] >= pd.to_datetime(fecha_inicio)) &
            (df_filtrado["FECHA"] <= pd.to_datetime(fecha_fin)) &
            (df_filtrado["IMPORTE"] >= min_val) &
            (df_filtrado["IMPORTE"] <= max_val)
        ]

        st.subheader("📋 Tabla de Transacciones")
        st.dataframe(df_filtrado, use_container_width=True)

        st.metric("💰 Total filtrado", f"{df_filtrado['IMPORTE'].sum():,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'))

        st.subheader("📊 Gráfica de Distribución")
        col_grafico = st.selectbox("Agrupar por:", ["CATEGORÍA", "COMERCIO", "SUBCATEGORÍA"])

        if col_grafico in df.columns:
            counts = df_filtrado[col_grafico].value_counts()
            if not counts.empty:
                fig, ax = plt.subplots(figsize=(6, 6))
                ax.pie(counts, labels=counts.index, autopct='%1.1f%%', startangle=140)
                ax.set_title(f'Distribución por {col_grafico}')
                ax.axis('equal')
                st.pyplot(fig)

        # 📈 Gráfico de evolución con predicción
        st.subheader("📈 Evolución Mensual de Gastos")
        años_disponibles = sorted(df_filtrado['AÑO'].dropna().unique())
        año_seleccionado = st.selectbox("Seleccionar año para la gráfica", años_disponibles, index=len(años_disponibles)-1)
        df_año = df_filtrado[df_filtrado['AÑO'] == año_seleccionado]

        df_año['AÑO_MES'] = df_año['FECHA'].dt.to_period('M')
        mensual = df_año.groupby('AÑO_MES')['IMPORTE'].sum().reset_index()
        mensual['AÑO_MES'] = mensual['AÑO_MES'].astype(str)
        mensual['MES_NUM'] = range(1, len(mensual) + 1)

        X = np.array(mensual['MES_NUM']).reshape(-1, 1)
        y = mensual['IMPORTE'].values
        modelo = LinearRegression().fit(X, y)
        futuros_meses = np.array(range(len(X)+1, len(X)+4)).reshape(-1, 1)
        predicciones = modelo.predict(futuros_meses)

        fig2, ax2 = plt.subplots(figsize=(10, 5))
        ax2.plot(mensual['AÑO_MES'], mensual['IMPORTE'], marker='o', label="Histórico", linewidth=2)
        futuras_labels = [f"{año_seleccionado}-{m:02d}" for m in range(len(X)+1, len(X)+4)]
        ax2.plot(futuras_labels, predicciones, linestyle='--', marker='x', color='gray', label="Predicción", linewidth=2)
        ax2.set_title("Evolución mensual y predicción de gastos")
        ax2.set_ylabel("Importe (€)")
        ax2.set_xlabel("Mes")
        ax2.legend()
        plt.xticks(rotation=45)
        st.pyplot(fig2)

        # Botón de descarga
        st.download_button(
            label="💾 Descargar CSV filtrado",
            data=df_filtrado.to_csv(index=False),
            file_name="gastos_filtrados.csv",
            mime="text/csv"
        )
