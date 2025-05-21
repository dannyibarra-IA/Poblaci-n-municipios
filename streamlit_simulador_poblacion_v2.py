
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Simulador de Proyección Poblacional", layout="centered")

st.title("Simulador de Proyección de Población")
st.write("Ingrese los datos para proyectar la población de su municipio usando distintos métodos.")

nombre = st.text_input("Nombre del municipio", "Mi Municipio")
P0 = st.number_input("Población inicial", min_value=0, value=100000)
metodo = st.selectbox("Método de proyección", ["Aritmético", "Geométrico", "Exponencial", "Wappaus"])
tasa = st.number_input("Tasa de crecimiento anual (%)", min_value=0.0, value=3.0, step=0.1)
t_horizonte = st.slider("Horizonte de proyección (años)", min_value=5, max_value=50, value=20)

# Convertimos la tasa a decimal
tasa_decimal = tasa / 100
t = np.arange(0, t_horizonte + 1)

# Cálculos según el método seleccionado
if metodo == "Aritmético":
    incremento = P0 * tasa_decimal
    P = P0 + incremento * t

elif metodo == "Geométrico":
    P = P0 * (1 + tasa_decimal)**t

elif metodo == "Exponencial":
    P = P0 * np.exp(tasa_decimal * t)

elif metodo == "Wappaus":
    n = t_horizonte
    Pn = P0 * (1 + tasa_decimal)**n
    P = P0 + ((Pn - P0)/n) * t + ((Pn - P0)/(2 * n**2)) * t**2

# Mostrar gráfico
st.subheader(f"Proyección para {nombre}")
fig, ax = plt.subplots()
ax.plot(t, P, label=f'{metodo}')
ax.set_title(f'Proyección poblacional usando el método {metodo}')
ax.set_xlabel("Años desde el inicio")
ax.set_ylabel("Población proyectada")
ax.grid(True)
ax.legend()
st.pyplot(fig)

# Mostrar tabla
df = pd.DataFrame({"Año": t, "Población proyectada": P.astype(int)})
st.subheader("Tabla de resultados")
st.dataframe(df)

# Botón para descargar
csv = df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Descargar resultados en Excel (CSV)",
    data=csv,
    file_name=f"proyeccion_{nombre.replace(' ', '_').lower()}.csv",
    mime="text/csv"
)
