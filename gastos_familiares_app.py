import streamlit as st
import pandas as pd

def asignar_categoria(row):
    tipo = str(row['TIPO']).lower()  # Convertir a string antes de usar .lower()
    
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

            #4. Asignar la columna categoría en base al valor de la columna TIPO
            df['Categoria'] = df.apply(asignar_categoria, axis=1)

            # **5. Filtrar solo los gastos (LO MÁS IMPORTANTE)**
            df = df[df['Categoria'] == 'Gasto']

            # **6. Imprimir valores únicos de la columna 'Categoria'**
            st.write("Valores únicos en la columna 'Categoria' (DESPUÉS del filtro):", df['Categoria'].unique())

            # 7. Mostrar datos (SOLO LAS TRANSACCIONES FILTRADAS)
            st.subheader('Transacciones de Gasto')
            st.dataframe(df)

            # 8. Resumen de gastos por categoría
            st.subheader('Gastos por Categoría')
            gastos_por_categoria = df.groupby('Categoria')['Importe'].sum().sort_values(ascending=False)
            st.bar_chart(gastos_por_categoria)

        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")

    else:
        st.info("Por favor, sube un archivo CSV para comenzar.")


if __name__ == "__main__":
    main()
