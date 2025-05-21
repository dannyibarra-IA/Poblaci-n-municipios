
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Simulador de Proyección Poblacional", layout="centered")

st.title("Simulador de Proyección de Población")
st.write("Ingrese los datos para proyectar la población de su municipio.")

nombre = st.text_input("Nombre del municipio", "Mi Municipio")
P0 = st.number_input("Población inicial", min_value=0, value=100000)
metodo = st.selectbox("Método de proyección", ["Aritmético", "Geométrico", "Exponencial", "Wappaus"])
Pn = st.number_input("Población esperada a n años", min_value=0, value=150000)
n = st.number_input("Años entre P0 y Pn", min_value=1, value=10)
t_horizonte = st.slider("Horizonte de proyección (años)", min_value=5, max_value=50, value=20)

t = np.arange(0, t_horizonte + 1)

if metodo == "Aritmético":
    r = (Pn - P0) / n
    P = P0 + r * t

elif metodo == "Geométrico":
    g = (Pn / P0)**(1/n) - 1
    P = P0 * (1 + g)**t

elif metodo == "Exponencial":
    g = (Pn / P0)**(1/n) - 1
    r = np.log(1 + g)
    P = P0 * np.exp(r * t)

elif metodo == "Wappaus":
    P = P0 + ((Pn - P0)/n) * t + ((Pn - P0)/(2 * n**2)) * t**2

# Mostrar resultados
st.subheader(f"Proyección para {nombre}")
fig, ax = plt.subplots()
ax.plot(t, P, label=f'{metodo}')
ax.set_title(f'Proyección poblacional usando el método {metodo}')
ax.set_xlabel("Años desde el inicio")
ax.set_ylabel("Población proyectada")
ax.grid(True)
ax.legend()
st.pyplot(fig)
