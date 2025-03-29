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
        st.error(f"Columnas encontradas: {df.columns.tolist()}\nSe esperaban: {list(columnas_esperadas)}")
    else:
        st.success("CSV cargado correctamente ✔️")

        # Filtros
        with st.sidebar:
            st.header("🔎 Filtros")
            concepto = st.text_input("Concepto contiene:")
            comercio = st.text_input("Comercio contiene:")
            categoria = st.text_input("Categoría contiene:")
            subcategoria = st.text_input("Subcategoría contiene:")

        filtro = pd.Series([True] * len(df))
        if concepto:
            filtro &= df["CONCEPTO"].str.contains(concepto, case=False, na=False)
        if comercio:
            filtro &= df["COMERCIO"].str.contains(comercio, case=False, na=False)
        if categoria:
            filtro &= df["CATEGORÍA"].str.contains(categoria, case=False, na=False)
        if subcategoria:
            filtro &= df["SUBCATEGORÍA"].str.contains(subcategoria, case=False, na=False)

        filtrado = df[filtro]
        st.dataframe(filtrado, use_container_width=True)

        # Agrupación y gráfica
        col1, col2 = st.columns(2)

        with col1:
            opcion_grafica = st.selectbox("📊 Gráfica por:", ["CATEGORÍA", "COMERCIO", "SUBCATEGORÍA"])
            if opcion_grafica:
                conteo = filtrado[opcion_grafica].value_counts()
                fig, ax = plt.subplots()
                ax.pie(conteo, labels=conteo.index, autopct="%1.1f%%", startangle=140)
                ax.set_title(f"Distribución por {opcion_grafica}")
                ax.axis('equal')
                st.pyplot(fig)

        with col2:
            st.download_button("💾 Descargar CSV filtrado", data=filtrado.to_csv(index=False), file_name="gastos_filtrados.csv", mime="text/csv")
