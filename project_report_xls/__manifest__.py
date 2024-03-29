# -*- coding: utf-8 -*-

{
    'author':  'Srikesh Infotech',
    'website': 'www.srikeshinfotech.com',
    'license': 'AGPL-3',
    'version': '11.0.0',
    'category': 'Project',
    'name': 'Project Report XLS',
    'depends': ['base', 'project', 'report_xlsx'],
    'license': 'AGPL-3',
    'summary': 'Project report in Excel',
    'description': '''
        Project report in Excel''',
    'data': [
             'wizard/project_report_wizard_view.xml',
             'views/project_report_template.xml',
             'views/project_report.xml'
             ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
