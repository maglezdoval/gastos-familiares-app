import streamlit as st
import pandas as pd

def main():
    st.title('Análisis de Gastos por Año y Mes')

    # 1. Permitir al usuario subir el archivo CSV
    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=["csv"])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, sep=';')

            # 2. Convertir la columna 'Fecha'
            df['Fecha'] = pd.to_datetime(df['AÑO'].astype(str) + '-' + df['MES'].astype(str) + '-' + df['DIA'].astype(str))

            # 3. Convertir la columna 'IMPORTE' a numérico
            df['Importe'] = df['IMPORTE'].str.replace(',', '.').astype(float)

            # 4. Crear una columna 'Tipo' basada en el importe
            df['Tipo'] = df['Importe'].apply(lambda x: 'Gasto' if x < 0 else 'Ingreso')

            # **5. Filtrar solo los gastos**
            df = df[df['Tipo'] == 'Gasto']

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
                index='Categoria',
                columns='Mes',
                aggfunc='sum',
                fill_value=0,  # Rellenar los valores faltantes con 0
                margins=True, # Añadir filas y columnas de totales
                margins_name='Total' # Renombrar "All" por "Total"
            )

            # Formatear la tabla para mostrar las cantidades en euros
            formato_euro = '{:,.0f}€'.format #Formatear la tabla para mostrar las cantidades en euros
            # Estilo para la tabla, incluyendo totales en negrita
            estilo = [
                {
                    'selector': 'th',
                    'props': [
                        ('background-color', '#6c757d !important'), # Color de fondo gris oscuro
                        ('color', 'white'),
                        ('font-weight', 'bold !important')
                    ]
                },
                {
                    'selector': 'th.col_heading',
                    'props': [('text-align', 'center')]
                },
                {
                    'selector': 'th.row_heading',
                    'props': [('text-align', 'left')]
                },
                 {
                    'selector': 'tr:last-child', #Selecciona la última fila (Total)
                    'props': [('font-weight' , 'bold !important')]

                 },
                 {
                   'selector': 'td:last-child', #Selecciona la última columna (Total)
                   'props': [('font-weight', 'bold !important')]
                  }
            ]

            # Formatear la tabla y aplicar estilo
            tabla_formateada = tabla_gastos.style.format(formatter=formato_euro).set_table_styles(estilo)

            # Mostrar la tabla
            st.dataframe(tabla_formateada, width=1000, height=500)

        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")

    else:
        st.info("Por favor, sube un archivo CSV para comenzar.")


if __name__ == "__main__":
    main()
