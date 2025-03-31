import streamlit as st
import pandas as pd

def main():
    st.title('Análisis de Gastos por Año y Mes')

    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=["csv"])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8')  # Intenta con UTF-8

            # Eliminar espacios en blanco en los nombres de las columnas
            df.columns = df.columns.str.strip()

            print(df.columns)  # Imprime los nombres de las columnas para verificar

            # *** Determina el nombre correcto de la columna (reemplaza 'IMPORTE' si es necesario) ***
            importe_column_name = 'IMPORTE'  # <--- ¡CAMBIA ESTO SI ES NECESARIO!
            tipo_column_name = 'TIPO'  # <-- ¡CAMBIA ESTO SI ES NECESARIO!
            categoria_column_name = 'CATEGORÍA' # <-- ¡CAMBIA ESTO SI ES NECESARIO!
            subcategoria_column_name = 'SUBCATEGORIA' # <-- ¡CAMBIA ESTO SI ES NECESARIO!
            anio_column_name = 'AÑO' # <-- ¡CAMBIA ESTO SI ES NECESARIO!
            mes_column_name = 'MES' # <-- ¡CAMBIA ESTO SI ES NECESARIO!
            dia_column_name = 'DIA' # <-- ¡CAMBIA ESTO SI ES NECESARIO!
            descripcion_column_name = 'DESCRIPCION' # <-- ¡CAMBIA ESTO SI ES NECESARIO!


            # Verificar si las columnas existen
            required_columns = [importe_column_name, tipo_column_name, categoria_column_name, subcategoria_column_name, anio_column_name, mes_column_name, dia_column_name, descripcion_column_name]
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                st.error(f"Error: Faltan las siguientes columnas en el archivo CSV: {', '.join(missing_columns)}")
                return

            # Convertir la columna 'IMPORTE' a numérico
            df['Importe'] = df[importe_column_name].str.replace(',', '.').astype(float)

            # 2. Convertir la columna 'Fecha'
            try:
                df['Fecha'] = pd.to_datetime(df[anio_column_name].astype(str) + '-' + df[mes_column_name].astype(str) + '-' + df[dia_column_name].astype(str), format='%Y-%m-%d')
            except ValueError as e:
                st.error(f"Error al convertir la columna 'Fecha': {e}.  Asegúrate de que las columnas AÑO, MES y DIA sean correctas.")
                return


            # **4. Verificamos los valores únicos de las columnas clave**
            st.write(f"Valores únicos en la columna '{tipo_column_name}':", df[tipo_column_name].unique())
            st.write(f"Valores únicos en la columna '{categoria_column_name}':", df[categoria_column_name].unique())

            # 5. Filtrar solo los gastos
            df = df[df[tipo_column_name] == "GASTO"]

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
                index=categoria_column_name,
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
            categoria_seleccionada = st.selectbox(f"Selecciona una Categoría ({categoria_column_name})", df_año[categoria_column_name].unique())
            mes_seleccionado= st.selectbox("Selecciona un Mes", df_año['Mes'].unique())

            # Crear filtro para la categoría y el mes seleccionados
            filtro = (df_año[categoria_column_name] == categoria_seleccionada) & (df_año['Mes'] == mes_seleccionado)

            # Agrupar por subcategoría y mostrar la tabla
            if filtro is not None:
                st.subheader(f"Detalle de Gastos para {categoria_seleccionada} en el mes {mes_seleccionado}")
                tabla_desglose = df_año[filtro].groupby([subcategoria_column_name, descripcion_column_name, 'Fecha'])['Importe'].sum().reset_index()
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
