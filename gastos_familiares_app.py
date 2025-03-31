import streamlit as st
import pandas as pd

def main():
    st.title('Análisis de Gastos por Año y Mes')

    # 1. Permitir al usuario subir el archivo CSV
    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=["csv"])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, sep=';')

            # Validación de columnas
            required_columns = ['AÑO', 'MES', 'DIA', 'IMPORTE', 'TIPO', 'CATEGORÍA', 'SUBCATEGORIA']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                st.error(f"Error: Faltan las siguientes columnas en el archivo CSV: {', '.join(missing_columns)}")
                return

            # 2. Convertir la columna 'Fecha'
            try:
                df['Fecha'] = pd.to_datetime(df['AÑO'].astype(str) + '-' + df['MES'].astype(str) + '-' + df['DIA'].astype(str), format='%Y-%m-%d')
            except ValueError as e:
                st.error(f"Error al convertir la columna 'Fecha': {e}.  Asegúrate de que las columnas AÑO, MES y DIA sean correctas.")
                return


            # 3. Convertir la columna 'IMPORTE' a numérico
            df['IMPORTE'] = df['IMPORTE'].str.replace(',', '.').astype(float)

            # Manejo de valores nulos en 'IMPORTE'
            if df['IMPORTE'].isnull().any():
                st.warning("Advertencia: Se encontraron valores nulos en la columna 'IMPORTE'. Se reemplazarán con 0.")
                df['IMPORTE'] = df['IMPORTE'].fillna(0)

            # **4. Verificamos los valores únicos de las columnas clave**
            st.write("Valores únicos en la columna 'TIPO':", df['TIPO'].unique())
            st.write("Valores únicos en la columna 'CATEGORÍA':", df['CATEGORÍA'].unique())

            # 5. Filtrar solo los gastos
            df = df[df["TIPO"] == "GASTO"]

            # 6. Extraer el año y el mes
            df['Año'] = df['Fecha'].dt.year
            df['Mes'] = df['Fecha'].dt.month

            # 7. Seleccionar el año
            año_seleccionado = st.selectbox("Selecciona un año", df['Año'].unique())

            # 8. Filtrar por año
            df_año = df[df['Año'] == año_seleccionado]

            # 9. Crear la tabla pivote
            tabla_gastos = df_año.pivot_table(
                values='Importe',
                index='CATEGORÍA',
                columns='Mes',
                aggfunc='sum',
                fill_value=0,
                margins=True,
                margins_name='Total'
            )

            # Formatear la tabla para mostrar las cantidades en euros
            formato_euro = '{:,.0f}€'.format
            estilo = [
                {'selector': 'th', 'props': [('background-color', '#6c757d !important'), ('color', 'white'), ('font-weight', 'bold !important')]},
                {'selector': 'th.col_heading', 'props': [('text-align', 'center')]},
                {'selector': 'th.row_heading', 'props': [('text-align', 'left')]},
                {'selector': 'tr:last-child', 'props': [('font-weight' , 'bold !important')]},
                {'selector': 'td:last-child', 'props': [('font-weight', 'bold !important')]}
            ]
            tabla_formateada = tabla_gastos.style.format(formatter=formato_euro).set_table_styles(estilo)

            # Mostrar la tabla
            st.dataframe(tabla_formateada, width=1000, height=500)

            # **15. Interactividad: Selección de celda con filtro por año**
            st.subheader("Detalle de Gastos")

            # Permitimos seleccionar la categoría del index para mostrar el desglose de los gastos mensuales
            categoria_seleccionada = st.selectbox("Selecciona una Categoría", df_año['CATEGORÍA'].unique())
            mes_seleccionado= st.selectbox("Selecciona un Mes", df_año['Mes'].unique())

            # Crear filtro para la categoría y el mes seleccionados
            filtro = (df_año['CATEGORÍA'] == categoria_seleccionada) & (df_año['Mes'] == mes_seleccionado)

            # Agrupar por subcategoría y mostrar la tabla
            if filtro is not None:
                st.subheader(f"Detalle de Gastos para {categoria_seleccionada} en el mes {mes_seleccionado}")
                tabla_desglose = df_año[filtro].groupby(['SUBCATEGORIA', 'DESCRIPCION', 'Fecha'])['Importe'].sum().reset_index()
                tabla_desglose = tabla_desglose.sort_values(by='Importe', ascending=False)
                st.dataframe(tabla_desglose)
            else:
                st.write("Selecciona una categoría y un mes de la tabla para ver el detalle.")


        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")

    else:
        st.info("Por favor, sube un archivo CSV para comenzar.")


if __name__ == "__main__":
    main()
