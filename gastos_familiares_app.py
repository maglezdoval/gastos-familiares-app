import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def asignar_categoria(row, categorias):
    descripcion = row['CONCEPTO'].lower()
    comercio = str(row['COMERCIO']).lower()

    # Priorizar la categoría y subcategoría si están definidas
    if not pd.isna(row['CATEGORÍA']) and row['CATEGORÍA'] != '':
        return row['CATEGORÍA']  # Usa la categoría existente

    # Buscar en la descripción
    for categoria, palabras_clave in categorias.items():
        for palabra in palabras_clave:
            if palabra in descripcion or palabra in comercio:
                return categoria

    return 'Otros'  # Si no coincide con ninguna palabra clave


def main():
    st.title('Gestor de Gastos Familiares')

    # 1. Permitir al usuario subir el archivo CSV
    uploaded_file = st.file_uploader("Sube tu archivo CSV", type=["csv"])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, sep=';')  # Usar el separador ';'

            # 2. Crear la columna 'Fecha'
            df['Fecha'] = pd.to_datetime(df['AÑO'].astype(str) + '-' + df['MES'].astype(str) + '-' + df['DIA'].astype(str))

            # 3. Convertir la columna 'IMPORTE' a numérico
            df['Importe'] = df['IMPORTE'].str.replace(',', '.').astype(float)

            # 4. Definir las categorías (puedes permitir al usuario editar esto)
            categorias = {
                'Alimentación': ['supermercado', 'carrefour', 'dia', 'alcampo', 'mercadona', 'hipercor', 'supercor', 'eroski', 'alimentación', 'fripesa', 'premium meat', 'varietal club', 'levadura madre', 'super yang','barrado', 'almacen frutas','el escudero','delicias manche','coop san isidro', 'M. Consuelo Sae','explaspedronera','obrador de javi','manacor','charcuteria tom','market las roza','24 horas la ria', 'tienda 24 horas','barrado', 'jamoncito','supermercado sp'],
                'Casa': ['alquiler', 'hipoteca', 'luz', 'agua', 'gas', 'internet', 'canal de isabel ii', 'iberdrola', 'podo', 'comunidad', 'canal de isabel','geo alternativa'],
                'Ocio': ['restaurante', 'cine', 'bar', 'netflix', 'spotify', 'teatro', 'concierto', 'vaca nostra', 'cervezas la vir', 'diver karting', 'estanco', 'copas', 'tapear', 'birras', 'starbucks', 'circo price', 'parque warner', 'bolera','maquinas vendin', 'pub', 'copas', 'el 17 moreto', 'the loft','kiosko','tagomago playa','tagomago beach','cafes mora', 'café', 'vending','terrraza de ming', 'arroz', 'arroz', 'bar isidro','bar las cadenas', 'boho market', 'chiringuito la', 'escondite de', 'atracciones luq', 'ilunion tartess', 'atracciones luq', 'market tartessu','vaca nostra','one hundred restrooms','one hundred restroom','cedipsa oficina','area comedor gr', 'circo price bar','el patio', 'area s. la gran', 'el patio','cedipsa e.s. mo','el 17 moreto','area s. la gran',' nyx*nordissocialconsul', 'alianza vendin','kiosko c/ kalam','est madrid atoc','serveo servicio', 'el escondite de', 'bar lenito', 'lacaile','parque guerra', 'la fuentona', 'parque warner', 'cinesa',Onneca Restaura','La Posada De Lo','Almagro Oro','lateral caleido','cabildo metropo','museo del foro','Secrets Caleido','Tacos Don Manol','The Loft', 'area s. La gran', 'El Patio'],
                'Transporte': ['gasolina', 'autobus', 'taxi', 'metro', 'carburante', 'cabify', 'autopista', 'autobus','coche', 'parking', 'cepsa hq madrid','impulsa eventos', 'auto pista', 'peaje', 'atpseitt aeropuert','autopista ap-36', 'autopista r4 se','cepsa hq madrid'],
                'Salud': ['farmacia', 'medico', 'dentista', 'hospital', 'farmacias', 'podologo','Farmacia Parque', 'Farmacia Gil Al', 'clinica narvart', 'servicios medicos','farmacia el bur', 'farmacia nativi', 'farmacia sada', 'clinica cemtro','farmacia','clinica narvart','Lcda Maria Paz Garcia','Farmacia Carlavilla','Farmaciachicano','Clínica Ojeda'],
                'Ropa': ['zara', 'h&m', 'c&a', 'decathlon', 'cortefiel', 'bershka', 'stradivarius','puma europe gmbh','converse 8111','coolmania', 'tienda gran pla','tienda 24 horas','mercado persa', 'sigler', 'market tartessu','nike', 'frikinh','lotería'],
                'Suministros': ['iberdrola smart', 'endesa', 'smart energy', 'suministros','iberdrola smart','suministros', 'elcogas','mercado libre','plenitude', 'podo', 'canal de isabel ii','geo alternativa'],
                'Otros': ['gastos varios', 'cajero automatico','diversión','Bizum', 'Sin Concepto',' Bizum Apth'],
                'Donaciones': ['aecc', 'cruz roja', 'fundacion corazon', 'donaciones', 'asociacion española contra el cancer', 'española contra el cancer','fundación corazón','fundacion española del corazon'],
                'Transferencia': ['transferencia', 'traspaso','CUENTA FAMILIAR', 'CUENTA COMÚN','cuenta familiar'],
                'Suscripciones': ['apple.com', 'netflix', 'hbo max', 'spotify', 'prime video', 'sky showtime', 'disney plus', 'wordpress','amazon prime','duolingo','telefónica','filmin','rakuten tv','spotify','juegos','tidal'],
                'Comisiones': ['comisiones','Santanderpremia','liquidación','intereses','tarjeta','comisión'],
                'Comunidad':['comunidad', 'propietarios','cp. modesto lafuente,','c. p. modesto lafuente'],
                'Supermercado':['mercadona','carrefour','dia','Simply'],
                'Cuidado Personal':['Alexso', 'Tijeritas Magic','Peluquería'],
                'Movistar':['Telefonica', 'Movistar'],
                'Limpieza': ['Sabbahi Meziou','Noufisa sabban meziane', 'Mina'],
                'Electrodomésticos':['Wizink', 'Financiera El Corte Inglés' ],
                'Transporte': ['Cabify'],
                'Alquiler': ['Fontanería']
            }

            # 5. Asignar categoría
            df['Categoria'] = df.apply(lambda row: asignar_categoria(row, categorias), axis=1)

            # 6. Crear una columna 'Tipo' basada en si el importe es positivo o negativo
            df['Importe'] = df['IMPORTE'].str.replace(',', '.').astype(float)
            df['Tipo'] = df['Importe'].apply(lambda x: 'Ingreso' if x > 0 else 'Gasto')

            # 7. Imprimir las categorías únicas encontradas
            print(df['Categoria'].unique())

            # 8. Mostrar datos
            st.subheader('Transacciones')
            st.dataframe(df)

            # 9. Resumen de gastos por categoría
            st.subheader('Gastos por Categoría')
            gastos_por_categoria = df.groupby('Categoria')['Importe'].sum().sort_values(ascending=False)
            st.bar_chart(gastos_por_categoria)

            # 10. Resumen de ingresos por categoría
            st.subheader('Ingresos por Categoría')
            ingresos_por_categoria = df[df['Tipo'] == 'Ingreso'].groupby('Categoria')['Importe'].sum().sort_values(ascending=False)
            st.bar_chart(ingresos_por_categoria)

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

            # Calcula el total de ingresos y egresos
            total_ingresos = df[df['Tipo'] == 'Ingreso']['Importe'].sum()
            total_egresos = df[df['Tipo'] == 'Gasto']['Importe'].sum()
            diferencia = total_ingresos + total_egresos  # Suma porque egresos son negativos

            # Muestra los resultados
            st.subheader('Resumen Financiero')
            st.write(f"Total de Ingresos: {total_ingresos:.2f}")
            st.write(f"Total de Egresos: {total_egresos:.2f}")
            st.write(f"Diferencia (Ingresos - Egresos): {diferencia:.2f}")

            #Visualización de pastel para ingresos y egresos totales
            st.subheader('Distribución de Ingresos y Egresos')
            labels = 'Ingresos', 'Egresos'
            sizes = [total_ingresos, abs(total_egresos)] # Asegurarse que los egresos sean positivos para la visualización
            colors = ['green', 'red']
            explode = (0.1, 0)  # Explode la primera slice (Ingresos)

            fig1, ax1 = plt.subplots()
            ax1.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%', shadow=True, startangle=90, colors=colors)
            ax1.axis('equal')  # Equal aspect ratio asegura que la torta se dibuje como un círculo.
            st.pyplot(fig1)  # Usar st.pyplot() para mostrar la figura de Matplotlib

        except Exception as e:
            st.error(f"Error al procesar el archivo: {e}")

    else:
        st.info("Por favor, sube un archivo CSV para comenzar.")


if __name__ == "__main__":
    main()
