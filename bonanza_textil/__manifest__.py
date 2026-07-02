{
    'name': 'Bonanza Textil - Fabricación',
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Fabricación de tela por maquila (sin BOM), consumo de hilo en '
               'consignación, producción por máquina y facturación por rollos',
    'description': """
Módulo de fabricación textil para empresas que trabajan bajo el esquema de
maquila: el cliente entrega su propio hilo (materia prima) y la empresa
únicamente transforma ese hilo en tela.

Incluye:
- Catálogos maestros: calibre, tipo de hilo, porcentaje de mezcla, agujado,
  tipo de tela, medida (loop) y máquinas.
- Órdenes de fabricación sin fórmula/BOM: se elige el hilo (cono/lote) y la
  cantidad directamente, con verificación de disponibilidad en tiempo real.
- Salida de mercadería automática al confirmar la fabricación (descuenta el
  hilo en consignación del cliente).
- Bitácora diaria de producción por máquina.
- Seguimiento de cantidades realizadas y generación de rollos, con
  facturación por rollo (kg).
- Ficha/ticket imprimible de la fabricación con detalle manual de conos.
""",
    'author': 'Bonanza Textil',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'contacts',
        'stock',
        'mail',
        'sale_management',
        'account',
    ],
    'data': [
        'security/textil_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/textil_product_data.xml',
        'views/textil_calibre_views.xml',
        'views/textil_tipo_hilo_views.xml',
        'views/textil_porcentaje_mezcla_views.xml',
        'views/textil_agujado_views.xml',
        'views/textil_tipo_tela_views.xml',
        'views/textil_medida_views.xml',
        'views/textil_maquina_views.xml',
        'views/textil_fabricacion_views.xml',
        'views/textil_rollo_views.xml',
        'views/textil_menus.xml',
        'report/textil_fabricacion_report.xml',
        'report/textil_fabricacion_report_templates.xml',
    ],
    'installable': True,
    'application': True,
}
