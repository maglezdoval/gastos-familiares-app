import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def asignar_categoria(row, categorias):
    descripcion = row['CONCEPTO'].lower()
    comercio = str(row['COMERCIO']).lower()
    categoria_manual = row.get('CATEGORÍA', None)  # Intenta obtener la categoría del archivo

    if not pd.isna(categoria_manual) and categoria_manual != '':
        return row['CATEGORÍA']  # Usa la categoría existente

    return 'Otros'  # Si no coincide con ninguna palabra clave

def main():
    st.title('Gestor de Gastos Familiares')

    # 1. Permitir al usuario subir el archivo CSV
    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=["csv"])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, sep=';')  # Usar el separador ';'

            # 2. Convertir la columna 'Fecha'
            df['Fecha'] = pd.to_datetime(df['AÑO'].astype(str) + '-' + df['MES'].astype(str) + '-' + df['DIA'].astype(str))

            # 3. Convertir la columna 'IMPORTE' a numérico
            df['Importe'] = df['IMPORTE'].str.replace(',', '.').astype(float)

            #4. Asignar la columna categoría
            df['Categoria'] = df.apply(asignar_categoria, axis=1, categorias={}) # Inicia vacío

            # 5. Crear una columna 'Tipo' basada en si el importe es positivo o negativo
            df['Tipo'] = df['Importe'].apply(lambda x: 'Ingreso' if x > 0 else 'Gasto')

            # **6. Filtrar solo los gastos**
            df = df[df['Tipo'] == 'Gasto']

            # 7. Imprimir las categorías únicas encontradas
            print(df['Categoria'].unique())

            # 8. Mostrar datos
            st.subheader('Transacciones')
            st.dataframe(df)

            # 9. Resumen de gastos por categoría
            st.subheader('Gastos por Categoría')
            gastos_por_categoria = df.groupby('Categoria')['Importe'].sum().sort_values(ascending=False)
            st.bar_chart(gastos_por_categoria)

            # **14. Sección de Análisis por Año y Mes**
            st.subheader('Análisis de Gastos por Año y Mes')

            # Extraer el año
            df['Año'] = df['Fecha'].dt.year
            df['Mes'] = df['Fecha'].dt.month

            #Seleccionar año
            año_seleccionado = st.selectbox("Selecciona un año", df['Año'].unique())

            #Filtrar por año
            df_año = df[df['Año'] == año_seleccionado]

            # Crear la tabla pivote
            tabla_gastos = df_año.pivot_table(
                values='Importe',
                index='Categoria',
                columns='Mes',
                aggfunc='sum',
                fill_value=0,  # Rellenar los valores faltantes con 0
                margins=True, # Añadir filas y columnas de totales
                margins_name='Total' # Renombrar "All" por "Total"
            )

           #Formatear la tabla para mostrar las cantidades en euros
            formato_euro = '{:,.0f}€'.format #Formatear la tabla para mostrar las cantidades en euros
            # Estilo para la tabla, incluyendo totales en negrita
            estilo = [
                {
                    'selector': 'th',
                    'props': [
                        ('background-color', '#6c757d !important'), # Color de fondo gris oscuro
                        ('color', 'white'),
                        ('font-weight', 'bold')
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
