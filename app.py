import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(page_title="Mi Caja Diaria", page_icon="📦", layout="centered")

# ==========================================
# 2. CONEXIÓN A GOOGLE SHEETS
# ==========================================
@st.cache_resource
def conectar_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
    cliente = gspread.authorize(creds)
    # ATENCIÓN: Reemplaza 'Caja_App' si tu Google Sheet se llama diferente
    sheet = cliente.open("Caja_App").sheet1 
    return sheet

sheet = conectar_sheets()

# ==========================================
# 3. INTERFAZ: REGISTRO DE OPERACIONES
# ==========================================
st.title("📦 Sistema de Caja Diaria")
st.markdown("---")

st.header("📝 Registrar Nueva Operación")

with st.form("registro_form"):
    tipo_op = st.selectbox("Tipo de Operación", ["Ingreso (Venta)", "Retiro", "Gasto"])
    metodo = st.radio("Método", ["Efectivo", "Mercado Pago (MP)"], horizontal=True)
    monto = st.number_input("Monto ($)", min_value=0.0, format="%.2f")
    
    subcategoria = "-"
    if tipo_op == "Retiro":
        subcategoria = st.selectbox("Destino del Retiro", ["Familia", "Propios"])
        
    observaciones = "-"
    if tipo_op in ["Retiro", "Gasto"]:
        observaciones = st.text_input("Observaciones (Opcional)")
        
    submit = st.form_submit_button("Guardar Operación")

if submit:
    if monto <= 0:
        st.error("El monto debe ser mayor a 0.")
    else:
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fila = [fecha_actual, tipo_op, metodo, subcategoria, monto, observaciones]
        sheet.append_row(fila)
        st.success(f"✅ Operación de {tipo_op} guardada con éxito.")

# ==========================================
# 4. DASHBOARD Y SALDOS
# ==========================================
st.markdown("---")
st.header("📊 Resumen de Saldos")

ocultar_saldos = st.toggle("👁️ Ocultar saldos", value=False)

try:
    datos = sheet.get_all_records()
    if datos:
        df = pd.DataFrame(datos)
        
        # Cálculos de saldos
        ingresos_efectivo = df[(df['Tipo'] == 'Ingreso (Venta)') & (df['Metodo'] == 'Efectivo')]['Monto'].sum()
        salidas_efectivo = df[(df['Tipo'].isin(['Retiro', 'Gasto'])) & (df['Metodo'] == 'Efectivo')]['Monto'].sum()
        saldo_efectivo = ingresos_efectivo - salidas_efectivo
        
        ingresos_mp = df[(df['Tipo'] == 'Ingreso (Venta)') & (df['Metodo'] == 'Mercado Pago (MP)')]['Monto'].sum()
        salidas_mp = df[(df['Tipo'].isin(['Retiro', 'Gasto'])) & (df['Metodo'] == 'Mercado Pago (MP)')]['Monto'].sum()
        saldo_mp = ingresos_mp - salidas_mp
        
        col1, col2, col3 = st.columns(3)
        
        def mostrar_monto(valor):
            return "***" if ocultar_saldos else f"${valor:,.2f}"

        col1.metric("💵 Saldo Efectivo", mostrar_monto(saldo_efectivo))
        col2.metric("📱 Saldo MP", mostrar_monto(saldo_mp))
        col3.metric("💰 SALDO TOTAL", mostrar_monto(saldo_efectivo + saldo_mp))
        
        st.subheader("Historial Reciente")
        if ocultar_saldos:
            st.info("El historial está oculto por privacidad.")
        else:
            st.dataframe(df.tail(10), use_container_width=True)

    else:
        st.info("No hay datos todavía. ¡Registra tu primera operación!")
except Exception as e:
    st.warning("⚠️ Asegúrate de que la primera fila de tu Google Sheet tenga estos títulos exactos: Fecha, Tipo, Metodo, Subcategoria, Monto, Observaciones")
