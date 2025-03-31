import streamlit as st
import pandas as pd

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

            # 4. Crear una columna 'Tipo' basada en el importe (INGRESOS O GASTOS)
            df['Tipo'] = df['Importe'].apply(lambda x: 'Gasto' if x < 0 else 'Ingreso')

            # **5. Filtrar solo los gastos (LO MÁS IMPORTANTE)**
            df = df[df['Tipo'] == 'Gasto']

            # **6. Imprimir valores únicos de la columna 'Tipo'**
            st.write("Valores únicos en la columna 'Tipo':", df['Tipo'].unique())

            # 7. Mostrar datos (SOLO LAS TRANSACCIONES FILTRADAS)
            st.subheader('Transacciones de Gasto')
            st.dataframe(df)

        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")

    else:
        st.info("Por favor, sube un archivo CSV para comenzar.")


if __name__ == "__main__":
    main()
