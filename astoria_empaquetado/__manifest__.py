{
    'name': 'Astoria - Conversión y Empaque',
    'version': '19.0.1.0.0',
    'author': 'Pablo Grunebaum',
    'category': 'Inventory/Inventory',
    'summary': 'Convierte producto a granel en presentaciones comerciales usando movimientos estándar de inventario (sin Fabricación).',
    'description': """
        Módulo de Conversión y Empaque
        ==============================
        Permite convertir un producto a granel en múltiples presentaciones
        comerciales desde una sola pantalla, sin usar Órdenes de Fabricación,
        utilizando únicamente stock.move / stock.move.line estándar.
        Preserva el costo (trasladado desde el producto a granel) y la
        trazabilidad completa por lote.
    """,
    'license': 'LGPL-3',
    'depends': ['stock', 'stock_account', 'product', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/product_template_views.xml',
        'views/stock_bulk_repack_views.xml',
        'views/stock_bulk_repack_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
