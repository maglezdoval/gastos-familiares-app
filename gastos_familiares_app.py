import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Gastos Familiares", layout="wide")
st.title("💸 Analizador de Gastos Familiares")

# Subida de archivo CSV
uploaded_file = st.file_uploader("📁 Sube tu archivo CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)

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

    columnas_esperadas = {"CONCEPTO", "COMERCIO", "CATEGORÍA", "SUBCATEGORÍA"}
    if not columnas_esperadas.issubset(df.columns):
        st.error(f"❌ Columnas encontradas: {df.columns.tolist()}\n✅ Se esperaban: {list(columnas_esperadas)}")
    else:
        st.success("✅ CSV cargado correctamente")

        # Filtros en la barra lateral
        st.sidebar.header("🔎 Filtros")
        concepto = st.sidebar.text_input("Filtrar por CONCEPTO")
        comercio = st.sidebar.text_input("Filtrar por COMERCIO")
        categoria = st.sidebar.text_input("Filtrar por CATEGORÍA")
        subcategoria = st.sidebar.text_input("Filtrar por SUBCATEGORÍA")

        # Aplicar filtros
        filtro = pd.Series([True] * len(df))
        if concepto:
            filtro &= df["CONCEPTO"].str.contains(concepto, case=False, na=False)
        if comercio:
            filtro &= df["COMERCIO"].str.contains(comercio, case=False, na=False)
        if categoria:
            filtro &= df["CATEGORÍA"].str.contains(categoria, case=False, na=False)
        if subcategoria:
            filtro &= df["SUBCATEGORÍA"].str.contains(subcategoria, case=False, na=False)

        df_filtrado = df[filtro]

        # Mostrar tabla
        st.subheader("📋 Tabla de Transacciones")
        st.dataframe(df_filtrado, use_container_width=True)

        # Selector de agrupación para gráfico
        st.subheader("📊 Gráfica de Distribución")
        col_grafico = st.selectbox("Agrupar por:", ["CATEGORÍA", "COMERCIO", "SUBCATEGORÍA"])

        # Gráfico de tarta
        if col_grafico in df.columns:
            counts = df_filtrado[col_grafico].value_counts()
            if not counts.empty:
                fig, ax = plt.subplots(figsize=(6, 6))
                ax.pie(counts, labels=counts.index, autopct='%1.1f%%', startangle=140)
                ax.set_title(f'Distribución por {col_grafico}')
                ax.axis('equal')
                st.pyplot(fig)
            else:
                st.info("No hay datos para graficar con los filtros actuales.")
        else:
            st.warning("Columna no válida para agrupar.")

        # Botón de descarga
        st.download_button(
            label="💾 Descargar CSV filtrado",
            data=df_filtrado.to_csv(index=False),
            file_name="gastos_filtrados.csv",
            mime="text/csv"
        )
else:
    st.info("👆 Sube un archivo CSV para comenzar.")
