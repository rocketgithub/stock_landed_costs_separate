# -*- coding: utf-8 -*-
{
    'name': "Costes en destino extra",

    'summary': """
        Extra funcionalidad para costes en destino""",

    'description': """
        Extra funcionalidad para costes en destino
    """,

    'author': "aquíH",
    'website': "http://www.aquih.com",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['stock_landed_costs'],

    'data': [
        'views/stock_landed_costs_individual_views.xml',
        'security/ir.model.access.csv',
    ],
}
