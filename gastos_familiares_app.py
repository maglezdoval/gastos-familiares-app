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

        # Secciones en la barra lateral
        seccion = st.sidebar.radio("Ir a sección:", ["🏠 Inicio", "📊 Análisis", "📈 Evolución", "✍️ Clasificación"])

        if seccion == "🏠 Inicio":
            st.header("🏠 Inicio y filtros")
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

        elif seccion == "📈 Evolución":
            st.header("📈 Evolución mensual de gastos")
            años_disponibles = sorted(df['AÑO'].dropna().unique())
            año_seleccionado = st.selectbox("Seleccionar año para la gráfica", años_disponibles, index=len(años_disponibles)-1)
            meses = list(range(1, 13))
            df_base = pd.DataFrame({"MES": meses})
            df_actual = df[df['AÑO'] == año_seleccionado].copy()
            mensual_actual = df_actual.groupby('MES')['IMPORTE'].sum().reset_index()
            df_merged = pd.merge(df_base, mensual_actual, on="MES", how="left").fillna(0)

            mostrar_prediccion = año_seleccionado == datetime.now().year
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

        elif seccion == "📊 Análisis":
            st.header("📊 Análisis e Insights")
            top_comercios = df.groupby("COMERCIO")["IMPORTE"].sum().sort_values(ascending=False).head(5)
            if not top_comercios.empty:
                st.subheader("🏪 Top 5 Comercios con más gasto")
                st.bar_chart(top_comercios)

            resumen = df.groupby(["AÑO", "MES"])["IMPORTE"].sum().reset_index()
            resumen.rename(columns={"IMPORTE": "TOTAL"}, inplace=True)
            resumen['TOTAL'] = resumen['TOTAL'].map(lambda x: f"{x:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.'))
            st.subheader("📅 Resumen por Año y Mes")
            st.dataframe(resumen, use_container_width=True)

            mes_actual = datetime.now().month
            anio_actual = datetime.now().year
            actual = df[(df['AÑO'] == anio_actual) & (df['MES'] == mes_actual)]

            if not actual.empty:
                mayor_gasto = actual.loc[actual['IMPORTE'].idxmax()]
                st.info(f"💥 Mayor gasto este mes: {mayor_gasto['IMPORTE']:,.2f} € en '{mayor_gasto['COMERCIO']}'".replace(',', 'X').replace('.', ',').replace('X', '.'))
                mes_anterior = mes_actual - 1 if mes_actual > 1 else 12
                anio_anterior = anio_actual if mes_actual > 1 else anio_actual - 1
                anterior = df[(df['AÑO'] == anio_anterior) & (df['MES'] == mes_anterior)]
                total_actual = actual['IMPORTE'].sum()
                total_anterior = anterior['IMPORTE'].sum() if not anterior.empty else 0
                diferencia = total_actual - total_anterior
                st.info(f"📈 Has gastado {diferencia:+,.2f} € {'más' if diferencia > 0 else 'menos'} que el mes pasado".replace(',', 'X').replace('.', ',').replace('X', '.'))

        elif seccion == "✍️ Clasificación":
            st.header("✍️ Clasificación y edición de transacciones")
            solo_vacias = st.checkbox("Mostrar solo sin categorizar")
            df_edit = df.copy()
            if solo_vacias:
                df_edit = df_edit[df_edit[['COMERCIO', 'CATEGORÍA', 'SUBCATEGORÍA']].isnull().any(axis=1)]

            for i, row in df_edit.iterrows():
                with st.expander(f"🧾 {row['CONCEPTO']} - {row['IMPORTE']} €"):
                    comercio_nuevo = st.text_input("Comercio", value=row['COMERCIO'] or "", key=f"comercio_{i}")
                    categoria_nueva = st.text_input("Categoría", value=row['CATEGORÍA'] or "", key=f"categoria_{i}")
                    subcat_nueva = st.text_input("Subcategoría", value=row['SUBCATEGORÍA'] or "", key=f"subcat_{i}")
                    df.at[i, 'COMERCIO'] = comercio_nuevo
                    df.at[i, 'CATEGORÍA'] = categoria_nueva
                    df.at[i, 'SUBCATEGORÍA'] = subcat_nueva

            st.download_button("💾 Descargar CSV actualizado", df.to_csv(index=False), file_name="gastos_actualizados.csv", mime="text/csv")
