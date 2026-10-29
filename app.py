import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA (Móvil)
# ==========================================
st.set_page_config(page_title="Caja Diaria", page_icon="📦", layout="centered")

# ==========================================
# 2. ESTILO GLOBAL: COUNTER STRIKE THEME
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&display=swap');
    
    /* Aplicar fuente táctica a todos los títulos, subtítulos y números de métricas */
    h1, h2, h3, .titulo-cs, .subtitulo-cs, div[data-testid="stMetricValue"] > div {
        font-family: 'Black Ops One', sans-serif !important;
        color: #E58D24 !important; /* Naranja CS */
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    
    .titulo-cs { font-size: 32px; }
    .subtitulo-cs { font-size: 22px; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. CONEXIÓN A GOOGLE SHEETS
# ==========================================
@st.cache_resource
def conectar_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    cliente = gspread.authorize(creds)
    sheet = cliente.open("Caja_App").sheet1 
    return sheet

sheet = conectar_sheets()

# ==========================================
# 4. INTERFAZ: REGISTRO DE OPERACIONES
# ==========================================
st.markdown('<div class="titulo-cs">📦 CAJA DIARIA</div>', unsafe_allow_html=True)
st.markdown("---")

st.markdown('<div class="subtitulo-cs">📝 NUEVA OPERACIÓN</div>', unsafe_allow_html=True)

tipo_op = st.selectbox("Tipo de Operación", ["Ingreso (Venta)", "Retiro", "Gasto"])

with st.form("registro_form"):
    metodo = st.selectbox("Método", ["Efectivo", "Mercado Pago (MP)"])
    monto = st.number_input("Monto ($)", min_value=0.0, format="%.2f", step=100.0)
    
    subcategoria = "-"
    if tipo_op == "Retiro":
        subcategoria = st.selectbox("Destino", ["Familia", "Propios"])
        
    observaciones = "-"
    if tipo_op in ["Retiro", "Gasto"]:
        observaciones = st.text_input("Observaciones (Opcional)")
        
    submit = st.form_submit_button("Guardar Operación", use_container_width=True)

if submit:
    if monto <= 0:
        st.error("El monto debe ser mayor a 0.")
    else:
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fila = [fecha_actual, tipo_op, metodo, subcategoria, monto, observaciones]
        sheet.append_row(fila)
        st.success(f"✅ {tipo_op} guardado.")
        st.rerun() # Recarga la app al instante para actualizar saldos

# ==========================================
# 5. DASHBOARD Y SALDOS
# ==========================================
st.markdown("---")
st.markdown('<div class="subtitulo-cs">📊 SALDOS</div>', unsafe_allow_html=True)

ocultar_saldos = st.toggle("👁️ Ocultar saldos", value=False)

try:
    # Traemos todos los valores (incluyendo encabezados para contar filas reales)
    todos_los_valores = sheet.get_all_values()
    
    if len(todos_los_valores) > 1:
        # Extraemos solo los datos para el DataFrame
        encabezados = todos_los_valores[0]
        filas_datos = todos_los_valores[1:]
        df = pd.DataFrame(filas_datos, columns=encabezados)
        
        # Convertir monto a número para poder sumar
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        
        # Cálculos
        ingresos_efectivo = df[(df['Tipo'] == 'Ingreso (Venta)') & (df['Metodo'] == 'Efectivo')]['Monto'].sum()
        salidas_efectivo = df[(df['Tipo'].isin(['Retiro', 'Gasto'])) & (df['Metodo'] == 'Efectivo')]['Monto'].sum()
        saldo_efectivo = ingresos_efectivo - salidas_efectivo
        
        ingresos_mp = df[(df['Tipo'] == 'Ingreso (Venta)') & (df['Metodo'] == 'Mercado Pago (MP)')]['Monto'].sum()
        salidas_mp = df[(df['Tipo'].isin(['Retiro', 'Gasto'])) & (df['Metodo'] == 'Mercado Pago (MP)')]['Monto'].sum()
        saldo_mp = ingresos_mp - salidas_mp
        
        def mostrar_monto(valor):
            return "***" if ocultar_saldos else f"${valor:,.2f}"

        col1, col2 = st.columns(2)
        col1.metric("💵 Efectivo", mostrar_monto(saldo_efectivo))
        col2.metric("📱 MP", mostrar_monto(saldo_mp))
        
        st.metric("💰 SALDO TOTAL", mostrar_monto(saldo_efectivo + saldo_mp))
        
        # ==========================================
        # 6. HISTORIAL ORDENADO Y ELIMINAR ÚLTIMA
        # ==========================================
        st.markdown("---")
        st.markdown('<div class="subtitulo-cs">📋 HISTORIAL RECIENTE</div>', unsafe_allow_html=True)
        
        if ocultar_saldos:
            st.info("Oculto por privacidad.")
        else:
            # Invertimos el DataFrame ([::-1]) para que lo más nuevo quede arriba
            df_invertido = df.iloc[::-1].head(10)
            st.dataframe(df_invertido, use_container_width=True)
        
        # Botón para eliminar la última operación
        st.write("¿Te equivocaste en la última carga?")
        if st.button("🗑️ Eliminar última operación", use_container_width=True):
            cantidad_filas = len(todos_los_valores)
            if cantidad_filas > 1: # Protege los encabezados de la fila 1
                sheet.delete_rows(cantidad_filas)
                st.success("Última operación eliminada con éxito.")
                st.rerun() # Recarga la app para refrescar datos
            else:
                st.warning("No hay operaciones para eliminar.")

    else:
        st.info("No hay datos todavía.")
except Exception as e:
    st.warning("⚠️ Verifica los títulos en tu Google Sheet. Detalles del error para el desarrollador: " + str(e))
