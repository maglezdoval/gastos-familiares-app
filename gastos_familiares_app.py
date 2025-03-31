import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def asignar_categoria(row, categorias):
    descripcion = row['CONCEPTO'].lower()
    comercio = str(row['COMERCIO']).lower()
    categoria_manual = row.get('CATEGORÍA', None)  # Intenta obtener la categoría del archivo

    if not pd.isna(categoria_manual) and categoria_manual != '':
        return categoria_manual

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

            # 10. Eliminar la sección de ingresos (ya no es necesaria)
            # Resumen de ingresos por categoría
            #st.subheader('Ingresos por Categoría')
            #ingresos_por_categoria = df[df['Tipo'] == 'Ingreso'].groupby('Categoria')['Importe'].sum().sort_values(ascending=False)
            #st.bar_chart(ingresos_por_categoria)

            # 11. Filtros (opcional)
            st.sidebar.header('Filtros')
            fecha_inicio = st.sidebar.date_input('Fecha Inicio', df['Fecha'].min())
            fecha_fin = st.sidebar.date_input('Fecha Fin', df['Fecha'].max())

            df_filtrado = df[(df['Fecha'] >= pd.to_datetime(fecha_inicio)) & (df['Fecha'] <= pd.to_datetime(fecha_fin))]
            st.subheader('Transacciones Filtradas')
            st.dataframe(df_filtrado)


            st.subheader('Gastos por Año y Categoría')
            df['Año'] = df['Fecha'].dt.year
            gastos_anuales = df.groupby(['Año', 'Categoria'])['Importe'].sum().unstack().fillna(0)
            st.line_chart(gastos_anuales)

            # 12. Eliminar el resumen financiero (ya no es necesario)
            # Calcula el total de ingresos y egresos
            #total_ingresos = df[df['Tipo'] == 'Ingreso']['Importe'].sum()
            #total_egresos = df[df['Tipo'] == 'Gasto']['Importe'].sum()
            #diferencia = total_ingresos + total_egresos  # Suma porque egresos son negativos

            # Muestra los resultados
            #st.subheader('Resumen Financiero')
            #st.write(f"Total de Ingresos: {total_ingresos:.2f}")
            #st.write(f"Total de Egresos: {total_egresos:.2f}")
            #st.write(f"Diferencia (Ingresos - Egresos): {diferencia:.2f}")

            #Visualización de pastel para ingresos y egresos totales
            #st.subheader('Distribución de Ingresos y Egresos')
            #labels = 'Ingresos', 'Egresos'
            #sizes = [total_ingresos, abs(total_egresos)] # Asegurarse que los egresos sean positivos para la visualización
            #colors = ['green', 'red']
            #explode = (0.1, 0)  # Explode la primera slice (Ingresos)

            #fig1, ax1 = plt.subplots()
            #ax1.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%', shadow=True, startangle=90, colors=colors)
            #ax1.axis('equal')  # Equal aspect ratio asegura que la torta se dibuje como un círculo.
            #st.pyplot(fig1)  # Usar st.pyplot() para mostrar la figura de Matplotlib


            # **13. Sección de Análisis Financiero en el sidebar**
            st.sidebar.header('Análisis Financiero')
            categoria_seleccionada = st.sidebar.selectbox("Selecciona una categoría", df['Categoria'].unique())

            # Filtrar por categoría seleccionada
            df_categoria = df[df['Categoria'] == categoria_seleccionada]

            # Mostrar transacciones de la categoría
            st.subheader(f'Transacciones de {categoria_seleccionada}')
            st.dataframe(df_categoria)

            # Resumen de gastos para la categoría seleccionada (mensual)
            st.subheader(f'Gastos Mensuales de {categoria_seleccionada}')
            gastos_mensuales = df_categoria.groupby(df_categoria['Fecha'].dt.strftime('%Y-%m'))['Importe'].sum()
            st.line_chart(gastos_mensuales)

        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")

    else:
        st.info("Por favor, sube un archivo CSV para comenzar.")

    #Visualización de pastel para ingresos y egresos totales
    if uploaded_file is not None:  # Mostrar solo si se ha cargado el archivo
        st.subheader('Distribución de Gastos Totales')
        gastos_totales_por_categoria = df.groupby('Categoria')['Importe'].sum()

        fig1, ax1 = plt.subplots()
        ax1.pie(gastos_totales_por_categoria, labels=gastos_totales_por_categoria.index, autopct='%1.1f%%', shadow=True, startangle=90)
        ax1.axis('equal')  # Equal aspect ratio asegura que la torta se dibuje como un círculo.
        st.pyplot(fig1)  # Usar st.pyplot() para mostrar la figura de Matplotlib



if __name__ == "__main__":
    main()
