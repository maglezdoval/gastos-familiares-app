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


if __name__ == "__main__":
    main()
