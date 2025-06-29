import streamlit as st

def load_custom_css():
    """Carga todos los estilos CSS personalizados de la aplicación"""
    st.markdown("""
    <style>
    /* === MÉTRICAS DE PROFESORES === */
    .metric-buenos {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border: 2px solid #28a745;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        color: #155724;
        box-shadow: 0 4px 15px rgba(40, 167, 69, 0.2);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .metric-buenos:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(40, 167, 69, 0.3);
    }
    
    .metric-malos {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        border: 2px solid #dc3545;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        color: #721c24;
        box-shadow: 0 4px 15px rgba(220, 53, 69, 0.2);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .metric-malos:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(220, 53, 69, 0.3);
    }
    
    .metric-neutros {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border: 2px solid #6c757d;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        color: #495057;
        box-shadow: 0 4px 15px rgba(108, 117, 125, 0.2);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .metric-neutros:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(108, 117, 125, 0.3);
    }
    
    .metric-total {
        background: linear-gradient(135deg, #e7f3ff 0%, #b8daff 100%);
        border: 2px solid #007bff;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        color: #004085;
        box-shadow: 0 4px 15px rgba(0, 123, 255, 0.2);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .metric-total:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0, 123, 255, 0.3);
    }
    
    .metric-number {
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
        line-height: 1;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .metric-label {
        font-size: 1.1rem;
        margin: 8px 0 0 0;
        font-weight: 600;
        opacity: 0.9;
        letter-spacing: 0.5px;
    }
    
    /* === COMENTARIOS DE PROFESORES === */
    .comentario-card {
        background: linear-gradient(145deg, #ffffff 0%, #f8f9fa 100%);
        border-left: 5px solid #007bff;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
        position: relative;
    }
    
    .comentario-card:hover {
        transform: translateX(5px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
    }
    
    .comentario-card::before {
        content: '"';
        position: absolute;
        top: 10px;
        left: 15px;
        font-size: 3rem;
        color: #007bff;
        opacity: 0.3;
        font-family: serif;
    }
    
    .comentario-header {
        font-weight: 700;
        color: #495057;
        margin-bottom: 12px;
        font-size: 1.1rem;
    }
    
    .comentario-text {
        font-style: italic;
        color: #6c757d;
        line-height: 1.6;
        font-size: 1rem;
        margin-left: 20px;
    }
    
    /* === BOTONES DE PROFESORES === */
    .profesor-row {
        background-color: #ffffff;
        border: 1px solid #dee2e6;
        border-radius: 10px;
        padding: 15px;
        margin: 8px 0;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    .profesor-row:hover {
        background-color: #f8f9fa;
        border-color: #007bff;
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    /* === TÍTULOS Y SUBTÍTULOS === */
    .section-title {
        color: #2c3e50;
        font-weight: 700;
        margin-bottom: 20px;
        padding-bottom: 10px;
        border-bottom: 3px solid #007bff;
        font-size: 1.5rem;
    }
    
    .profesor-title {
        color: #34495e;
        font-weight: 600;
        margin-bottom: 15px;
        font-size: 1.3rem;
    }
    
    /* === RESPONSIVE DESIGN === */
    @media (max-width: 768px) {
        .metric-number {
            font-size: 2rem;
        }
        
        .metric-label {
            font-size: 1rem;
        }
        
        .comentario-card {
            padding: 15px;
            margin: 10px 0;
        }
        
        .comentario-text {
            font-size: 0.9rem;
        }
    }
    
    @media (max-width: 480px) {
        .metric-number {
            font-size: 1.5rem;
        }
        
        .metric-label {
            font-size: 0.9rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

def render_metric_card(value, label, metric_type):
    """Renderiza una tarjeta de métrica con el estilo correspondiente"""
    return f"""
    <div class="metric-{metric_type}">
        <p class="metric-number">{value}</p>
        <p class="metric-label">{label}</p>
    </div>
    """

def render_comentario_card(numero, comentario):
    """Renderiza una tarjeta de comentario estilizada"""
    return f"""
    <div class="comentario-card">
        <div class="comentario-header">Comentario {numero}</div>
        <div class="comentario-text">{comentario}</div>
    </div>
    """

def render_section_title(title):
    """Renderiza un título de sección estilizado"""
    return f'<h2 class="section-title">{title}</h2>'

def render_profesor_title(nombre):
    """Renderiza el título del profesor"""
    return f'<h3 class="profesor-title">Comentarios sobre {nombre}</h3>'