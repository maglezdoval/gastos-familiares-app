import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="Gastos Familiares", layout="wide")
st.title("💸 Analizador de Gastos Familiares")

# Subida de archivo CSV
uploaded_file = st.file_uploader("📁 Sube tu archivo CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')

    # Normaliza nombres de columnas
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
        # Procesar importe y fecha
        df['IMPORTE'] = df['IMPORTE'].astype(str).str.replace(',', '.').astype(float)
        df[['AÑO', 'MES', 'DIA']] = df[['AÑO', 'MES', 'DIA']].apply(pd.to_numeric, errors='coerce')
        def construir_fecha_segura(row):
    try:
        return datetime(int(row['AÑO']), int(row['MES']), int(row['DIA']))
    except:
        return pd.NaT

df['FECHA'] = df.apply(construir_fecha_segura, axis=1)

        st.success("✅ CSV cargado correctamente")

        # Filtros en la barra lateral
        st.sidebar.header("🔎 Filtros")
        concepto = st.sidebar.text_input("Filtrar por CONCEPTO")

        comercio = st.sidebar.selectbox("Filtrar por COMERCIO", ["Todos"] + sorted(df['COMERCIO'].dropna().unique().tolist()))
        categoria = st.sidebar.selectbox("Filtrar por CATEGORÍA", ["Todos"] + sorted(df['CATEGORÍA'].dropna().unique().tolist()))
        subcategoria = st.sidebar.selectbox("Filtrar por SUBCATEGORÍA", ["Todos"] + sorted(df['SUBCATEGORÍA'].dropna().unique().tolist()))

        cuenta = st.sidebar.selectbox("Filtrar por CUENTA", ["Todos"] + sorted(df['CUENTA'].dropna().unique().tolist()) if 'CUENTA' in df.columns else ["Todos"])
        tipo = st.sidebar.selectbox("Filtrar por TIPO", ["Todos"] + sorted(df['TIPO'].dropna().unique().tolist()) if 'TIPO' in df.columns else ["Todos"])

        # Filtro de fechas
        fecha_min = df['FECHA'].min()
        fecha_max = df['FECHA'].max()
        fecha_inicio, fecha_fin = st.sidebar.date_input("Filtrar por rango de fechas", [fecha_min, fecha_max])

        # Filtro por importe
        importe_min = float(df['IMPORTE'].min())
        importe_max = float(df['IMPORTE'].max())
        min_val, max_val = st.sidebar.slider("Filtrar por IMPORTE", min_value=importe_min, max_value=importe_max, value=(importe_min, importe_max))

        # Aplicar filtros
        filtro = pd.Series([True] * len(df))
        if concepto:
            filtro &= df["CONCEPTO"].str.contains(concepto, case=False, na=False)
        if comercio != "Todos":
            filtro &= df["COMERCIO"] == comercio
        if categoria != "Todos":
            filtro &= df["CATEGORÍA"] == categoria
        if subcategoria != "Todos":
            filtro &= df["SUBCATEGORÍA"] == subcategoria
        if cuenta != "Todos" and 'CUENTA' in df.columns:
            filtro &= df["CUENTA"] == cuenta
        if tipo != "Todos" and 'TIPO' in df.columns:
            filtro &= df["TIPO"] == tipo
        filtro &= (df['FECHA'] >= pd.to_datetime(fecha_inicio)) & (df['FECHA'] <= pd.to_datetime(fecha_fin))
        filtro &= (df['IMPORTE'] >= min_val) & (df['IMPORTE'] <= max_val)

        df_filtrado = df[filtro]

        # Mostrar tabla y resumen
        st.subheader("📋 Tabla de Transacciones")
        st.dataframe(df_filtrado, use_container_width=True)

        st.metric("💰 Total filtrado", f"{df_filtrado['IMPORTE'].sum():,.2f} €")

        # Selector de agrupación para gráfico de tarta
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

        # Gráfico de evolución mensual
        st.subheader("📈 Evolución Mensual de Gastos")
        df_filtrado['AÑO_MES'] = df_filtrado['FECHA'].dt.to_period('M')
        mensual = df_filtrado.groupby('AÑO_MES')['IMPORTE'].sum().reset_index()
        mensual['AÑO_MES'] = mensual['AÑO_MES'].astype(str)

        fig2, ax2 = plt.subplots()
        ax2.plot(mensual['AÑO_MES'], mensual['IMPORTE'], marker='o')
        ax2.set_title("Evolución de los importes mensuales")
        ax2.set_ylabel("Importe (€)")
        ax2.set_xlabel("Mes")
        plt.xticks(rotation=45)
        st.pyplot(fig2)

        # Botón de descarga
        st.download_button(
            label="💾 Descargar CSV filtrado",
            data=df_filtrado.to_csv(index=False),
            file_name="gastos_filtrados.csv",
            mime="text/csv"
        )
else:
    st.info("👆 Sube un archivo CSV para comenzar.")
