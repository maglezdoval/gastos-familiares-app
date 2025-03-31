import streamlit as st
import pandas as pd

def asignar_categoria(row):
    tipo = str(row['TIPO']).lower()
    
    if tipo == 'gasto':
        return 'Gasto'  # O la categoría que quieras para los gastos
    elif tipo == 'ingreso':
        return 'Ingreso'  # O la categoría que quieras para los ingresos
    elif tipo == 'traspaso':
        return 'Traspaso' #Categorización de los Traspasos
    elif tipo == 'recibo':
        return 'Recibo' #Categorización de los Recibos
    return 'Otros'  # Para cualquier otro caso


def main():
    st.title('Gestor de Gastos Familiares - SOLO GASTOS')

    # 1. Permitir al usuario subir el archivo CSV
    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=["csv"])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, sep=';')

            # 2. Convertir la columna 'Fecha'
            df['Fecha'] = pd.to_datetime(df['AÑO'].astype(str) + '-' + df['MES'].astype(str) + '-' + df['DIA'].astype(str))

            # 3. Convertir la columna 'IMPORTE' a numérico
            df['Importe'] = df['IMPORTE'].str.replace(',', '.').astype(float)

            # 4. Asignar la columna categoría en base al valor de la columna TIPO
            df['Categoria'] = df.apply(asignar_categoria, axis=1)

            # **5. Filtrar solo los gastos (LO MÁS IMPORTANTE)**
            df = df[df['Categoria'] == 'Gasto']

            # 7. Imprimir las categorías únicas encontradas
            print(df['Categoria'].unique())

            # 8. Mostrar datos
            st.subheader('Transacciones de Gasto')
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
